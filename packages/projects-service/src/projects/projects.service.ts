import {
  Inject,
  Injectable,
  HttpException,
  HttpStatus,
  ForbiddenException,
  Logger,
} from '@nestjs/common';
import { eq, and, sql } from 'drizzle-orm';
import * as crypto from 'crypto';
import {
  DRIZZLE_RW,
  DRIZZLE_RO,
  type Database,
  type User,
  projects,
  events,
  votes,
  users,
  eventAttendees,
  projectCollaborators,
  getFeatureFlagsList,
  BAD_ACCESS,
  PlatformSettingsService,
} from '@podium/shared';
import { isItchUrl, ItchValidatorService } from './validators/itch-validator';
import { GitHubValidatorService } from './validators/github-validator';

@Injectable()
export class ProjectsService {
  private readonly logger = new Logger(ProjectsService.name);

  constructor(
    @Inject(DRIZZLE_RW) private readonly dbRw: Database,
    @Inject(DRIZZLE_RO) private readonly dbRo: Database,
    private readonly itchValidator: ItchValidatorService,
    private readonly githubValidator: GitHubValidatorService,
    private readonly platformSettings: PlatformSettingsService,
  ) {}

  private generateJoinCode(): string {
    // 5 random bytes → 8 base64url chars → ~1 trillion combinations.
    // Collision probability is negligible; uniqueness is enforced by the DB
    // UNIQUE constraint on join_code. The caller retries on conflict.
    return crypto.randomBytes(5).toString('base64url').toUpperCase().slice(0, 8);
  }

  /**
   * Verify that the user is a superadmin OR the POC/owner/RM of the project's event.
   * Throws ForbiddenException if not authorized.
   */
  private async assertEventLeadership(eventId: string, user: User): Promise<void> {
    if (user.is_superadmin) return;

    const event = await this.dbRw.query.events.findFirst({
      where: eq(events.id, eventId),
    });
    if (!event) {
      throw new HttpException('Event not found', HttpStatus.NOT_FOUND);
    }

    if (getFeatureFlagsList(event).includes('flagship')) {
      throw new ForbiddenException('Superadmin access required for flagship events');
    }

    if (
      event.owner_id === user.id ||
      event.poc_id === user.id ||
      event.rm_id === user.id
    ) {
      return;
    }

    throw new ForbiddenException('Only the event POC or superadmins can perform this action');
  }

  async getMyProjects(user: User) {
    // Run both queries in parallel, use SQL COUNT instead of loading all vote rows
    const projectSelect = {
      id: projects.id,
      name: projects.name,
      repo: projects.repo,
      image_url: projects.image_url,
      demo: projects.demo,
      description: projects.description,
      owner_id: projects.owner_id,
      join_code: projects.join_code,
      hours_spent: projects.hours_spent,
      event_id: projects.event_id,
      points: sql<number>`(SELECT count(*) FROM votes WHERE votes.project_id = "projects"."id")`.mapWith(Number),
    };

    const [ownedProjects, collabProjects] = await Promise.all([
      this.dbRo
        .select(projectSelect)
        .from(projects)
        .where(eq(projects.owner_id, user.id)),
      this.dbRo
        .select(projectSelect)
        .from(projectCollaborators)
        .innerJoin(projects, eq(projectCollaborators.project_id, projects.id))
        .where(eq(projectCollaborators.user_id, user.id)),
    ]);

    const allProjects = [...ownedProjects, ...collabProjects];

    // Filter out flagship event projects for non-superadmins
    if (!user.is_superadmin) {
      const eventIds = [...new Set(allProjects.map((p) => p.event_id))];
      if (eventIds.length > 0) {
        const flagshipEventIds = new Set<string>();
        const eventRows = await this.dbRo.query.events.findMany({
          where: sql`${events.id} IN (${sql.join(eventIds.map((id) => sql`${id}`), sql`, `)})`,
          columns: { id: true, feature_flags_csv: true },
        });
        for (const e of eventRows) {
          if (getFeatureFlagsList(e).includes('flagship')) {
            flagshipEventIds.add(e.id);
          }
        }
        return allProjects.filter((p) => !flagshipEventIds.has(p.event_id));
      }
    }

    return allProjects;
  }

  async createProject(
    data: {
      name: string;
      repo: string;
      image_url: string;
      demo?: string;
      description?: string;
      hours_spent?: number;
      event_id: string;
      teammates?: {
        email: string;
        first_name?: string;
        last_name?: string;
        phone?: string;
        street_1?: string;
        street_2?: string;
        city?: string;
        state?: string;
        zip_code?: string;
        country?: string;
        dob?: string;
      }[];
    },
    user: User,
  ) {
    // Run all prerequisite checks in parallel against primary — they guard the write.
    const [event, attendeeRow, existingProject] = await Promise.all([
      this.dbRw.query.events.findFirst({ where: eq(events.id, data.event_id) }),
      this.dbRw.query.eventAttendees.findFirst({
        where: and(
          eq(eventAttendees.event_id, data.event_id),
          eq(eventAttendees.user_id, user.id),
        ),
      }),
      this.dbRw.query.projects.findFirst({
        where: and(
          eq(projects.event_id, data.event_id),
          eq(projects.owner_id, user.id),
        ),
      }),
    ]);

    if (!event) {
      throw new HttpException('Event not found', HttpStatus.NOT_FOUND);
    }
    // Block non-superadmins from creating projects in flagship events
    if (!user.is_superadmin && getFeatureFlagsList(event).includes('flagship')) {
      throw new HttpException('Event not found', HttpStatus.NOT_FOUND);
    }
    if (!event.enabled) {
      throw new HttpException('Event is not open', HttpStatus.FORBIDDEN);
    }
    if (event.votable) {
      throw new HttpException(
        'Submissions are closed — voting has already started',
        HttpStatus.FORBIDDEN,
      );
    }
    if (!event.demo_links_optional && !(data.demo && data.demo.trim())) {
      throw new HttpException(
        'Demo URL is required for this event',
        HttpStatus.UNPROCESSABLE_ENTITY,
      );
    }
    if (!attendeeRow) {
      throw new ForbiddenException('Owner not part of event');
    }
    if (existingProject) {
      throw new HttpException(
        'You have already submitted a project for this event',
        HttpStatus.CONFLICT,
      );
    }

    // Fetch platform-level validation toggles (sub-ms Redis reads)
    const [githubEnabled, itchEnabled] = await Promise.all([
      this.platformSettings.isGitHubValidationEnabled(),
      this.platformSettings.isItchValidationEnabled(),
    ]);

    // Validate GitHub repo is accessible (cached + rate-limited)
    // null = rate-limited (429), skip the check rather than blocking the user
    if (githubEnabled && (await this.githubValidator.isRepoAccessible(data.repo)) === false) {
      throw new HttpException(
        'GitHub repository not found — make sure the URL is correct and the repo is public',
        HttpStatus.UNPROCESSABLE_ENTITY,
      );
    }

    // Validate itch.io demo link if provided
    // Skip itch checks entirely if disabled for this specific event
    if (data.demo && data.demo.trim() && !event.itch_verification_disabled) {
      if (!isItchUrl(data.demo)) {
        throw new HttpException(
          'Demo URL must be an itch.io game page (e.g. https://username.itch.io/game)',
          HttpStatus.UNPROCESSABLE_ENTITY,
        );
      }
      // Rate-limited: queued at max 1 req/sec to itch.io
      // null = rate-limited (429), skip the check rather than blocking the user
      if (itchEnabled && (await this.itchValidator.isPlayable(data.demo)) === false) {
        throw new HttpException(
          "Game is not browser-playable — enable 'Run game in browser' in your itch.io project settings",
          HttpStatus.UNPROCESSABLE_ENTITY,
        );
      }
    }

    if (event.ysws_checks_enabled) {
      const fullUser = await this.dbRw.query.users.findFirst({
        where: eq(users.id, user.id),
      });
      if (!fullUser) {
        throw new HttpException('User not found', HttpStatus.NOT_FOUND);
      }

      const missing: string[] = [];
      if (!fullUser.street_1) missing.push('street address');
      if (!fullUser.city) missing.push('city');
      if (!fullUser.state) missing.push('state/province');
      if (!fullUser.zip_code) missing.push('zip/postal code');
      if (!fullUser.country) missing.push('country');
      if (!fullUser.dob) missing.push('date of birth');

      if (missing.length > 0) {
        throw new HttpException(
          { message: 'Please complete your profile before submitting a project', missing_fields: missing },
          HttpStatus.UNPROCESSABLE_ENTITY,
        );
      }

      // Age check: must be under 19 at time of submission
      const dob = new Date(fullUser.dob!);
      const now = new Date();
      let age = now.getFullYear() - dob.getFullYear();
      const monthDiff = now.getMonth() - dob.getMonth();
      if (monthDiff < 0 || (monthDiff === 0 && now.getDate() < dob.getDate())) {
        age--;
      }
      if (age >= 19) {
        throw new HttpException(
          'You must be under 19 years old to submit a project for this event',
          HttpStatus.FORBIDDEN,
        );
      }
    }

    // Attempt the insert with a fresh join code. On the rare collision the DB
    // UNIQUE constraint fires; retry up to 3 times before giving up.
    for (let attempt = 0; attempt < 3; attempt++) {
      try {
        const [saved] = await this.dbRw
          .insert(projects)
          .values({
            name: data.name,
            repo: data.repo,
            image_url: data.image_url,
            demo: data.demo || '',
            description: data.description || '',
            hours_spent: data.hours_spent ?? 0,
            event_id: data.event_id,
            owner_id: user.id,
            join_code: this.generateJoinCode(),
          })
          .returning();

        // Process teammates after project creation
        if (data.teammates?.length) {
          await this.addTeammates(saved.id, data.event_id, data.teammates, user);
        }

        return { id: saved.id, join_code: saved.join_code };
      } catch (err: any) {
        // Postgres unique_violation code = '23505'
        if (err?.code === '23505' && err?.constraint?.includes('join_code')) {
          this.logger.warn(`join_code collision on attempt ${attempt + 1}, retrying`);
          continue;
        }
        throw err;
      }
    }

    throw new HttpException(
      'Failed to generate unique join code',
      HttpStatus.INTERNAL_SERVER_ERROR,
    );
  }

  private async addTeammates(
    projectId: string,
    eventId: string,
    teammates: {
      email: string;
      first_name?: string;
      last_name?: string;
      phone?: string;
      street_1?: string;
      street_2?: string;
      city?: string;
      state?: string;
      zip_code?: string;
      country?: string;
      dob?: string;
    }[],
    owner: User,
  ) {
    for (const mate of teammates) {
      const email = mate.email.trim().toLowerCase();
      if (email === owner.email) continue; // skip self

      let teammate = await this.dbRw.query.users.findFirst({
        where: eq(users.email, email),
      });

      if (!teammate) {
        // Create user with the provided fields
        const [created] = await this.dbRw
          .insert(users)
          .values({
            email,
            first_name: mate.first_name || email.split('@')[0],
            last_name: mate.last_name ?? '',
            display_name: mate.first_name || email.split('@')[0],
            phone: mate.phone ?? '',
            street_1: mate.street_1 ?? '',
            street_2: mate.street_2 ?? '',
            city: mate.city ?? '',
            state: mate.state ?? '',
            zip_code: mate.zip_code ?? '',
            country: mate.country ?? '',
            dob: mate.dob ?? null,
          })
          .returning();
        teammate = created;
      } else {
        // Fill in only the empty fields — never overwrite existing data
        const updates: Record<string, any> = {};
        if (!teammate.first_name && mate.first_name) updates.first_name = mate.first_name;
        if (!teammate.last_name && mate.last_name) updates.last_name = mate.last_name;
        if (!teammate.phone && mate.phone) updates.phone = mate.phone;
        if (!teammate.street_1 && mate.street_1) updates.street_1 = mate.street_1;
        if (!teammate.street_2 && mate.street_2) updates.street_2 = mate.street_2;
        if (!teammate.city && mate.city) updates.city = mate.city;
        if (!teammate.state && mate.state) updates.state = mate.state;
        if (!teammate.zip_code && mate.zip_code) updates.zip_code = mate.zip_code;
        if (!teammate.country && mate.country) updates.country = mate.country;
        if (!teammate.dob && mate.dob) updates.dob = mate.dob;

        if (Object.keys(updates).length > 0) {
          await this.dbRw.update(users).set(updates).where(eq(users.id, teammate.id));
        }
      }

      // Add as event attendee (ignore if already attending)
      await this.dbRw
        .insert(eventAttendees)
        .values({ event_id: eventId, user_id: teammate.id })
        .onConflictDoNothing();

      // Add as project collaborator (ignore if already a collaborator)
      await this.dbRw
        .insert(projectCollaborators)
        .values({ project_id: projectId, user_id: teammate.id })
        .onConflictDoNothing();
    }
  }

  async joinProject(joinCode: string, user: User) {
    const project = await this.dbRw.query.projects.findFirst({
      where: eq(projects.join_code, joinCode.toUpperCase()),
    });
    if (!project) {
      throw new HttpException('No project found', HttpStatus.NOT_FOUND);
    }

    // Block non-superadmins from joining flagship event projects
    if (!user.is_superadmin) {
      const event = await this.dbRw.query.events.findFirst({
        where: eq(events.id, project.event_id),
        columns: { feature_flags_csv: true },
      });
      if (event && getFeatureFlagsList(event).includes('flagship')) {
        throw new HttpException('No project found', HttpStatus.NOT_FOUND);
      }
    }

    if (user.id === project.owner_id) {
      throw new HttpException(
        'User is already a collaborator or owner',
        HttpStatus.BAD_REQUEST,
      );
    }

    const existingCollab = await this.dbRw.query.projectCollaborators.findFirst({
      where: and(
        eq(projectCollaborators.project_id, project.id),
        eq(projectCollaborators.user_id, user.id),
      ),
    });
    if (existingCollab) {
      throw new HttpException(
        'User is already a collaborator or owner',
        HttpStatus.BAD_REQUEST,
      );
    }

    const attendeeRow = await this.dbRw.query.eventAttendees.findFirst({
      where: and(
        eq(eventAttendees.event_id, project.event_id),
        eq(eventAttendees.user_id, user.id),
      ),
    });
    if (!attendeeRow) {
      throw BAD_ACCESS;
    }

    await this.dbRw.insert(projectCollaborators).values({
      project_id: project.id,
      user_id: user.id,
    });

    return { message: 'Successfully joined project' };
  }

  async updateProject(
    projectId: string,
    data: Record<string, any>,
    user: User,
  ) {
    const project = await this.dbRw.query.projects.findFirst({
      where: eq(projects.id, projectId),
    });
    if (!project || project.owner_id !== user.id) {
      throw BAD_ACCESS;
    }

    const event = await this.dbRw.query.events.findFirst({
      where: eq(events.id, project.event_id),
    });
    if (!event) {
      throw new HttpException('Event not found', HttpStatus.NOT_FOUND);
    }

    const demoValue = data.demo !== undefined ? data.demo : project.demo;
    if (
      !event.demo_links_optional &&
      !(demoValue && demoValue.trim())
    ) {
      throw new HttpException(
        'Demo URL is required for this event',
        HttpStatus.UNPROCESSABLE_ENTITY,
      );
    }

    const updateData: Record<string, any> = {};
    for (const [key, value] of Object.entries(data)) {
      if (value !== undefined && value !== null) {
        updateData[key] = value;
      }
    }

    const [saved] = await this.dbRw
      .update(projects)
      .set(updateData)
      .where(eq(projects.id, projectId))
      .returning();

    // Get vote count without loading all vote rows
    const [{ count }] = await this.dbRw
      .select({ count: sql<number>`count(*)`.mapWith(Number) })
      .from(votes)
      .where(eq(votes.project_id, projectId));

    return {
      id: saved.id,
      name: saved.name,
      repo: saved.repo,
      image_url: saved.image_url,
      demo: saved.demo,
      description: saved.description,
      points: count,
      owner_id: saved.owner_id,
    };
  }

  async deleteProject(projectId: string, user: User) {
    const project = await this.dbRw.query.projects.findFirst({
      where: eq(projects.id, projectId),
    });
    if (!project || project.owner_id !== user.id) {
      throw BAD_ACCESS;
    }
    await this.dbRw.delete(projects).where(eq(projects.id, projectId));
    return { message: 'Project deleted' };
  }

  async getProject(projectId: string, user?: User | null) {
    const rows = await this.dbRo
      .select({
        id: projects.id,
        name: projects.name,
        repo: projects.repo,
        image_url: projects.image_url,
        demo: projects.demo,
        description: projects.description,
        owner_id: projects.owner_id,
        owner_name: users.display_name,
        event_id: projects.event_id,
        points: sql<number>`(SELECT count(*) FROM votes WHERE votes.project_id = "projects"."id")`.mapWith(Number),
      })
      .from(projects)
      .innerJoin(users, eq(projects.owner_id, users.id))
      .where(eq(projects.id, projectId))
      .limit(1);

    if (rows.length === 0) {
      throw new HttpException('Project not found', HttpStatus.NOT_FOUND);
    }

    // Block access to flagship event projects for non-superadmins
    if (!user?.is_superadmin) {
      const event = await this.dbRo.query.events.findFirst({
        where: eq(events.id, rows[0].event_id),
        columns: { feature_flags_csv: true },
      });
      if (event && getFeatureFlagsList(event).includes('flagship')) {
        throw new HttpException('Project not found', HttpStatus.NOT_FOUND);
      }
    }

    // Fetch collaborators — only return display_name (no email PII for participants)
    const collabRows = await this.dbRo
      .select({
        user_id: users.id,
        display_name: users.display_name,
      })
      .from(projectCollaborators)
      .innerJoin(users, eq(projectCollaborators.user_id, users.id))
      .where(eq(projectCollaborators.project_id, projectId));

    return {
      ...rows[0],
      collaborators: collabRows,
    };
  }

  // ── Admin methods ──────────────────────────────────────────────────

  async adminUpdateProject(projectId: string, data: Record<string, any>, user: User) {
    const project = await this.dbRw.query.projects.findFirst({
      where: eq(projects.id, projectId),
    });
    if (!project) {
      throw new HttpException('Project not found', HttpStatus.NOT_FOUND);
    }

    await this.assertEventLeadership(project.event_id, user);

    const allowedFields = ['name', 'repo', 'image_url', 'demo', 'description', 'hours_spent'];
    const updateData: Record<string, any> = {};
    for (const [key, value] of Object.entries(data)) {
      if (allowedFields.includes(key) && value !== undefined) {
        updateData[key] = value;
      }
    }

    if (Object.keys(updateData).length > 0) {
      await this.dbRw
        .update(projects)
        .set(updateData)
        .where(eq(projects.id, projectId));
    }

    const rows = await this.dbRw
      .select({
        id: projects.id,
        name: projects.name,
        repo: projects.repo,
        image_url: projects.image_url,
        demo: projects.demo,
        description: projects.description,
        owner_id: projects.owner_id,
        points: sql<number>`(SELECT count(*) FROM votes WHERE votes.project_id = "projects"."id")`.mapWith(Number),
      })
      .from(projects)
      .where(eq(projects.id, projectId))
      .limit(1);

    return rows[0];
  }

  async adminDeleteProject(projectId: string, user: User) {
    const project = await this.dbRw.query.projects.findFirst({
      where: eq(projects.id, projectId),
    });
    if (!project) {
      throw new HttpException('Project not found', HttpStatus.NOT_FOUND);
    }

    await this.assertEventLeadership(project.event_id, user);

    await this.dbRw.delete(projectCollaborators).where(eq(projectCollaborators.project_id, projectId));
    await this.dbRw.delete(votes).where(eq(votes.project_id, projectId));
    await this.dbRw.delete(projects).where(eq(projects.id, projectId));
    return { message: 'Project deleted' };
  }

  async adminAddCollaborator(
    projectId: string,
    data: {
      email: string;
      first_name?: string;
      last_name?: string;
      phone?: string;
      street_1?: string;
      street_2?: string;
      city?: string;
      state?: string;
      zip_code?: string;
      country?: string;
      dob?: string;
    },
    user: User,
  ) {
    const project = await this.dbRw.query.projects.findFirst({
      where: eq(projects.id, projectId),
    });
    if (!project) {
      throw new HttpException('Project not found', HttpStatus.NOT_FOUND);
    }

    await this.assertEventLeadership(project.event_id, user);

    const email = data.email.trim().toLowerCase();

    // Check if email is the project owner
    const owner = await this.dbRw.query.users.findFirst({
      where: eq(users.id, project.owner_id),
    });
    if (owner && owner.email === email) {
      throw new HttpException('Cannot add the project owner as a collaborator', HttpStatus.BAD_REQUEST);
    }

    let teammate = await this.dbRw.query.users.findFirst({
      where: eq(users.email, email),
    });

    if (!teammate) {
      const [created] = await this.dbRw
        .insert(users)
        .values({
          email,
          first_name: data.first_name || email.split('@')[0],
          last_name: data.last_name ?? '',
          display_name: data.first_name || email.split('@')[0],
          phone: data.phone ?? '',
          street_1: data.street_1 ?? '',
          street_2: data.street_2 ?? '',
          city: data.city ?? '',
          state: data.state ?? '',
          zip_code: data.zip_code ?? '',
          country: data.country ?? '',
          dob: data.dob ?? null,
        })
        .returning();
      teammate = created;
    } else {
      // Fill in only empty fields
      const updates: Record<string, any> = {};
      if (!teammate.first_name && data.first_name) updates.first_name = data.first_name;
      if (!teammate.last_name && data.last_name) updates.last_name = data.last_name;
      if (!teammate.phone && data.phone) updates.phone = data.phone;
      if (!teammate.street_1 && data.street_1) updates.street_1 = data.street_1;
      if (!teammate.street_2 && data.street_2) updates.street_2 = data.street_2;
      if (!teammate.city && data.city) updates.city = data.city;
      if (!teammate.state && data.state) updates.state = data.state;
      if (!teammate.zip_code && data.zip_code) updates.zip_code = data.zip_code;
      if (!teammate.country && data.country) updates.country = data.country;
      if (!teammate.dob && data.dob) updates.dob = data.dob;

      if (Object.keys(updates).length > 0) {
        await this.dbRw.update(users).set(updates).where(eq(users.id, teammate.id));
      }
    }

    // Add as event attendee
    await this.dbRw
      .insert(eventAttendees)
      .values({ event_id: project.event_id, user_id: teammate.id })
      .onConflictDoNothing();

    // Add as project collaborator
    await this.dbRw
      .insert(projectCollaborators)
      .values({ project_id: projectId, user_id: teammate.id })
      .onConflictDoNothing();

    return {
      user_id: teammate.id,
      display_name: teammate.display_name,
      email: teammate.email,
    };
  }

  async adminRemoveCollaborator(projectId: string, userId: string, user: User) {
    const project = await this.dbRw.query.projects.findFirst({
      where: eq(projects.id, projectId),
    });
    if (!project) {
      throw new HttpException('Project not found', HttpStatus.NOT_FOUND);
    }

    await this.assertEventLeadership(project.event_id, user);

    await this.dbRw
      .delete(projectCollaborators)
      .where(
        and(
          eq(projectCollaborators.project_id, projectId),
          eq(projectCollaborators.user_id, userId),
        ),
      );

    return { message: 'Collaborator removed' };
  }

  async ownerAddCollaborator(
    projectId: string,
    data: {
      email: string;
      first_name?: string;
      last_name?: string;
      phone?: string;
      street_1?: string;
      street_2?: string;
      city?: string;
      state?: string;
      zip_code?: string;
      country?: string;
      dob?: string;
    },
    user: User,
  ) {
    const project = await this.dbRw.query.projects.findFirst({
      where: eq(projects.id, projectId),
    });
    if (!project) {
      throw new HttpException('Project not found', HttpStatus.NOT_FOUND);
    }
    if (project.owner_id !== user.id) {
      throw BAD_ACCESS;
    }

    const event = await this.dbRw.query.events.findFirst({
      where: eq(events.id, project.event_id),
    });
    if (!event) {
      throw new HttpException('Event not found', HttpStatus.NOT_FOUND);
    }
    if (!event.votable && !event.voting_closed) {
      throw new HttpException(
        'Teammates can only be edited after submissions close',
        HttpStatus.FORBIDDEN,
      );
    }
    if (!user.is_superadmin && getFeatureFlagsList(event).includes('flagship')) {
      throw new HttpException('Project not found', HttpStatus.NOT_FOUND);
    }

    const email = data.email.trim().toLowerCase();
    if (email === user.email) {
      throw new HttpException('Cannot add yourself as a collaborator', HttpStatus.BAD_REQUEST);
    }

    let teammate = await this.dbRw.query.users.findFirst({
      where: eq(users.email, email),
    });

    if (!teammate) {
      const [created] = await this.dbRw
        .insert(users)
        .values({
          email,
          first_name: data.first_name || email.split('@')[0],
          last_name: data.last_name ?? '',
          display_name: data.first_name || email.split('@')[0],
          phone: data.phone ?? '',
          street_1: data.street_1 ?? '',
          street_2: data.street_2 ?? '',
          city: data.city ?? '',
          state: data.state ?? '',
          zip_code: data.zip_code ?? '',
          country: data.country ?? '',
          dob: data.dob ?? null,
        })
        .returning();
      teammate = created;
    } else {
      const updates: Record<string, any> = {};
      if (!teammate.first_name && data.first_name) updates.first_name = data.first_name;
      if (!teammate.last_name && data.last_name) updates.last_name = data.last_name;
      if (!teammate.phone && data.phone) updates.phone = data.phone;
      if (!teammate.street_1 && data.street_1) updates.street_1 = data.street_1;
      if (!teammate.street_2 && data.street_2) updates.street_2 = data.street_2;
      if (!teammate.city && data.city) updates.city = data.city;
      if (!teammate.state && data.state) updates.state = data.state;
      if (!teammate.zip_code && data.zip_code) updates.zip_code = data.zip_code;
      if (!teammate.country && data.country) updates.country = data.country;
      if (!teammate.dob && data.dob) updates.dob = data.dob;

      if (Object.keys(updates).length > 0) {
        await this.dbRw.update(users).set(updates).where(eq(users.id, teammate.id));
      }
    }

    await this.dbRw
      .insert(eventAttendees)
      .values({ event_id: project.event_id, user_id: teammate.id })
      .onConflictDoNothing();

    await this.dbRw
      .insert(projectCollaborators)
      .values({ project_id: projectId, user_id: teammate.id })
      .onConflictDoNothing();

    return {
      user_id: teammate.id,
      display_name: teammate.display_name,
    };
  }

  async ownerRemoveCollaborator(projectId: string, userId: string, user: User) {
    const project = await this.dbRw.query.projects.findFirst({
      where: eq(projects.id, projectId),
    });
    if (!project) {
      throw new HttpException('Project not found', HttpStatus.NOT_FOUND);
    }
    if (project.owner_id !== user.id) {
      throw BAD_ACCESS;
    }

    const event = await this.dbRw.query.events.findFirst({
      where: eq(events.id, project.event_id),
    });
    if (!event) {
      throw new HttpException('Event not found', HttpStatus.NOT_FOUND);
    }
    if (!event.votable && !event.voting_closed) {
      throw new HttpException(
        'Teammates can only be edited after submissions close',
        HttpStatus.FORBIDDEN,
      );
    }

    await this.dbRw
      .delete(projectCollaborators)
      .where(
        and(
          eq(projectCollaborators.project_id, projectId),
          eq(projectCollaborators.user_id, userId),
        ),
      );

    return { message: 'Collaborator removed' };
  }

  async validateProject(projectId: string) {
    const project = await this.dbRo.query.projects.findFirst({
      where: eq(projects.id, projectId),
    });
    if (!project) {
      throw new HttpException('Project not found', HttpStatus.NOT_FOUND);
    }

    if (!project.demo) {
      return { valid: false, message: 'No demo URL provided' };
    }

    if (!isItchUrl(project.demo)) {
      return {
        valid: false,
        message: 'Demo URL must be an itch.io game page',
      };
    }

    if (!(await this.platformSettings.isItchValidationEnabled())) {
      return { valid: true, message: 'Itch validation is currently disabled' };
    }

    const playable = await this.itchValidator.isPlayable(project.demo);
    if (playable === null) {
      return { valid: true, message: 'Itch.io rate limit hit, skipping check' };
    }
    if (playable) {
      return { valid: true, message: 'Game is browser-playable' };
    }

    return {
      valid: false,
      message:
        "Game is not browser-playable. Enable 'Run game in browser' in your itch.io project settings.",
    };
  }
}
