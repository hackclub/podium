import {
  Inject,
  Injectable,
  HttpException,
  HttpStatus,
  ForbiddenException,
} from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { eq, and, sql, inArray } from 'drizzle-orm';
import { Subject, Observable } from 'rxjs';
import { filter, map } from 'rxjs/operators';
import type Redis from 'ioredis';
import {
  DRIZZLE_RW,
  DRIZZLE_RO,
  DRIZZLE_R,
  REDIS,
  type Database,
  type User,
  events,
  projects,
  votes,
  users,
  eventAttendees,
  projectCollaborators,
  getMaxVotesPerUser,
  getFeatureFlagsList,
  PlatformSettingsService,
} from '@podium/shared';

function mapEventPublic(e: any) {
  return {
    id: e.id,
    name: e.name,
    slug: e.slug,
    description: e.description,
    enabled: e.enabled,
    votable: e.votable,
    voting_closed: e.voting_closed,
    leaderboard_enabled: e.leaderboard_enabled,
    demo_links_optional: e.demo_links_optional,
    max_votes_per_user: getMaxVotesPerUser(),
    ysws_checks_enabled: e.ysws_checks_enabled,
    feature_flags_csv: e.feature_flags_csv,
    theme_name: e.theme_name,
    theme_background: e.theme_background,
    theme_font: e.theme_font,
    theme_primary: e.theme_primary,
    theme_selected: e.theme_selected,
  };
}

@Injectable()
export class EventsService {
  private readonly activeEventSeries: string;
  private readonly enableTestEndpoints: boolean;
  private readonly cockpitApiKey: string;
  private readonly airtableApiKey: string;
  private readonly airtableBaseId: string;
  private readonly airtableTableId: string;

  /** Cached Cockpit scan counts: slug → counts. Refreshed every 2 minutes. */
  private cockpitScanCache: {
    data: Map<string, { checkin_count: number; scanned_day1_count: number; scanned_day2_count: number; scanned_either_day_count: number }>;
    fetchedAt: number;
  } | null = null;
  private cockpitScanCachePromise: Promise<void> | null = null;
  private static readonly SCAN_CACHE_TTL_MS = 2 * 60 * 1000; // 2 minutes

  /** SSE subject — emits { eventId, data } whenever stage flags change. */
  private readonly stageChange$ = new Subject<{ eventId: string; data: any }>();

  /** Subscribe to stage changes for a specific event. Returns an Observable for NestJS SSE. */
  subscribeToStageChanges(eventId: string): Observable<{ data: any }> {
    return this.stageChange$.pipe(
      filter((msg) => msg.eventId === eventId),
      map((msg) => ({ data: msg.data })),
    );
  }

  private static readonly DASHBOARD_CACHE_KEY = 'podium:campfire-dashboard';
  private static readonly DASHBOARD_CACHE_TTL = 300; // 5 minutes

  constructor(
    @Inject(DRIZZLE_RW) private readonly dbRw: Database,
    @Inject(DRIZZLE_RO) private readonly dbRo: Database,
    @Inject(DRIZZLE_R) private readonly dbR: Database,
    @Inject(REDIS) private readonly redis: Redis,
    private readonly config: ConfigService,
    private readonly platformSettings: PlatformSettingsService,
  ) {
    this.activeEventSeries = config.get<string>(
      'PODIUM_ACTIVE_EVENT_SERIES',
      '',
    )!;
    this.enableTestEndpoints =
      config.get<string>('PODIUM_ENABLE_TEST_ENDPOINTS', 'false') === 'true';
    this.cockpitApiKey = config.get<string>('COCKPIT_API_KEY', '')!;
    this.airtableApiKey = config.get<string>('AIRTABLE_API_KEY', '')!;
    this.airtableBaseId = config.get<string>('AIRTABLE_BASE_ID', '')!;
    this.airtableTableId = config.get<string>('AIRTABLE_TABLE_ID', '')!;
  }

  /**
   * Throws 404 if the event has the 'flagship' flag and the caller is not a superadmin.
   * Call this at the top of any public endpoint that accepts an event ID.
   */
  private assertNotFlagship(
    event: { feature_flags_csv: string | null } | null | undefined,
    user?: User | null,
  ): asserts event is { feature_flags_csv: string | null } {
    if (!event) {
      throw new HttpException('Event not found', HttpStatus.NOT_FOUND);
    }
    if (!user?.is_superadmin && getFeatureFlagsList(event as { feature_flags_csv: string }).includes('flagship')) {
      throw new HttpException('Event not found', HttpStatus.NOT_FOUND);
    }
  }

  async listOfficialEvents(user?: User | null) {
    const rows = await this.dbR
      .select({ event: events })
      .from(events)
      .where(eq(events.enabled, true));

    return rows
      .filter((r) => user?.is_superadmin || !getFeatureFlagsList(r.event).includes('flagship'))
      .map((r) => mapEventPublic(r.event));
  }

  async getEventById(eventId: string, user?: User | null) {
    const row = await this.dbRo.query.events.findFirst({
      where: eq(events.id, eventId),
    });

    this.assertNotFlagship(row, user);
    return mapEventPublic(row);
  }

  async getAttendingEvents(user: User) {
    const rows = await this.dbRo
      .select({ event: events })
      .from(eventAttendees)
      .innerJoin(events, eq(eventAttendees.event_id, events.id))
      .where(eq(eventAttendees.user_id, user.id));

    return {
      attending_events: rows
        .filter((r) => user.is_superadmin || !getFeatureFlagsList(r.event).includes('flagship'))
        .map((r) => mapEventPublic(r.event)),
    };
  }

  async getMyVotes(eventId: string, user: User): Promise<string[]> {
    const event = await this.dbRo.query.events.findFirst({
      where: eq(events.id, eventId),
      columns: { feature_flags_csv: true },
    });
    this.assertNotFlagship(event, user);

    const rows = await this.dbRo.query.votes.findMany({
      where: and(eq(votes.event_id, eventId), eq(votes.voter_id, user.id)),
      columns: { project_id: true },
    });
    return rows.map((r) => r.project_id);
  }

  async checkVotable(eventId: string): Promise<void> {
    const event = await this.dbRw.query.events.findFirst({
      where: eq(events.id, eventId),
      columns: { votable: true, voting_closed: true },
    });
    if (!event) {
      throw new HttpException('Event not found', HttpStatus.NOT_FOUND);
    }
    if (!event.votable) {
      throw new HttpException('Voting is not enabled for this event', HttpStatus.FORBIDDEN);
    }
    if (event.voting_closed) {
      throw new HttpException('Voting is closed for this event', HttpStatus.FORBIDDEN);
    }
  }

  /** Auto-registers the user as an attendee if they aren't already. */
  async ensureAttendee(eventId: string, userId: string): Promise<void> {
    const attendee = await this.dbRw.query.eventAttendees.findFirst({
      where: and(
        eq(eventAttendees.event_id, eventId),
        eq(eventAttendees.user_id, userId),
      ),
    });
    if (!attendee) {
      await this.dbRw
        .insert(eventAttendees)
        .values({ event_id: eventId, user_id: userId })
        .onConflictDoNothing();
    }
  }

  async checkNotOwnProject(userId: string, projectIds: string[]): Promise<void> {
    if (projectIds.length === 0) return;

    // Batch both lookups into single queries instead of N+1
    const [ownedProjects, collabRows] = await Promise.all([
      this.dbRo.query.projects.findMany({
        where: inArray(projects.id, projectIds),
        columns: { id: true, owner_id: true },
      }),
      this.dbRo.query.projectCollaborators.findMany({
        where: and(
          inArray(projectCollaborators.project_id, projectIds),
          eq(projectCollaborators.user_id, userId),
        ),
        columns: { project_id: true },
      }),
    ]);

    for (const project of ownedProjects) {
      if (project.owner_id === userId) {
        throw new HttpException('You cannot vote for your own project', HttpStatus.FORBIDDEN);
      }
    }

    if (collabRows.length > 0) {
      throw new HttpException('You cannot vote for a project you collaborated on', HttpStatus.FORBIDDEN);
    }
  }

  async attendEvent(eventId: string, user: User) {
    const event = await this.dbRw.query.events.findFirst({
      where: eq(events.id, eventId),
    });
    this.assertNotFlagship(event, user);

    if (!event.enabled) {
      throw new HttpException('Event is not enabled', HttpStatus.BAD_REQUEST);
    }

    const existing = await this.dbRw.query.eventAttendees.findFirst({
      where: and(
        eq(eventAttendees.event_id, eventId),
        eq(eventAttendees.user_id, user.id),
      ),
    });

    if (existing) {
      return {
        message: 'Already attending this event',
        event_id: event.id,
      };
    }

    await this.dbRw.insert(eventAttendees).values({
      event_id: eventId,
      user_id: user.id,
    });

    return { message: 'Successfully joined event', event_id: event.id };
  }

  async getEventProjects(eventId: string, leaderboard: boolean, user?: User | null) {
    const event = await this.dbRo.query.events.findFirst({
      where: eq(events.id, eventId),
    });
    this.assertNotFlagship(event, user);

    const isFlagship = getFeatureFlagsList(event as { feature_flags_csv: string }).includes('flagship');

    // Flagship events use manual_points; normal events use vote count
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
        points: isFlagship
          ? projects.manual_points
          : sql<number>`(SELECT count(*) FROM votes WHERE votes.project_id = "projects"."id")`.mapWith(Number),
      })
      .from(projects)
      .innerJoin(users, eq(projects.owner_id, users.id))
      .where(eq(projects.event_id, eventId));

    // Fetch collaborators for all projects in one query
    const projectIds = rows.map((r) => r.id);
    const collabRows = projectIds.length
      ? await this.dbRo
          .select({
            project_id: projectCollaborators.project_id,
            user_id: users.id,
            display_name: users.display_name,
          })
          .from(projectCollaborators)
          .innerJoin(users, eq(projectCollaborators.user_id, users.id))
          .where(inArray(projectCollaborators.project_id, projectIds))
      : [];

    const collabsByProject = new Map<string, { user_id: string; display_name: string }[]>();
    for (const c of collabRows) {
      const list = collabsByProject.get(c.project_id) ?? [];
      list.push({ user_id: c.user_id, display_name: c.display_name });
      collabsByProject.set(c.project_id, list);
    }

    const result = rows.map((p) => ({
      ...p,
      collaborators: collabsByProject.get(p.id) ?? [],
    }));

    if (leaderboard) {
      if (!event.leaderboard_enabled) {
        throw new ForbiddenException('Leaderboard is not enabled');
      }
      result.sort((a, b) => b.points - a.points);
    } else {
      for (let i = result.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [result[i], result[j]] = [result[j], result[i]];
      }
    }

    return result;
  }

  async getUniqueVoterCount(eventId: string, user?: User | null): Promise<{ unique_voters: number }> {
    const event = await this.dbR.query.events.findFirst({
      where: eq(events.id, eventId),
      columns: { feature_flags_csv: true },
    });
    this.assertNotFlagship(event, user);

    const [row] = await this.dbR
      .select({
        unique_voters: sql<number>`COUNT(DISTINCT ${votes.voter_id})`.mapWith(Number),
      })
      .from(votes)
      .where(eq(votes.event_id, eventId));

    return { unique_voters: row?.unique_voters ?? 0 };
  }

  async getEventIdBySlug(slug: string, user?: User | null): Promise<{ id: string }> {
    const event = await this.dbRo.query.events.findFirst({
      where: eq(events.slug, slug),
    });
    this.assertNotFlagship(event, user);
    return { id: event.id };
  }

  // ── Admin methods ──────────────────────────────────────────────────

  async adminListEvents(user: User) {
    // Use SQL counts instead of loading all projects/votes/attendees into memory
    const rows = await this.dbRo
      .select({
        event: events,
        attendee_count: sql<number>`(SELECT count(*) FROM event_attendees WHERE event_attendees.event_id = "events"."id")`.mapWith(Number),
        project_count: sql<number>`(SELECT count(*) FROM projects WHERE projects.event_id = "events"."id")`.mapWith(Number),
        vote_count: sql<number>`(SELECT count(*) FROM votes WHERE votes.event_id = "events"."id")`.mapWith(Number),
      })
      .from(events);

    let filtered = rows;
    if (!user.is_superadmin) {
      // For non-superadmins, check if user owns or attends the event
      const attendingEventIds = new Set(
        (await this.dbRo.query.eventAttendees.findMany({
          where: eq(eventAttendees.user_id, user.id),
          columns: { event_id: true },
        })).map((a) => a.event_id),
      );

      filtered = rows.filter(
        (r) =>
          // Flagship events are superadmin-only
          !getFeatureFlagsList(r.event).includes('flagship') &&
          (r.event.owner_id === user.id ||
            r.event.poc_id === user.id ||
            r.event.rm_id === user.id ||
            (user.is_admin && attendingEventIds.has(r.event.id))),
      );
    }

    return filtered.map((r) => ({
      ...mapEventPublic(r.event),
      owner_id: r.event.owner_id,
      poc_id: r.event.poc_id,
      rm_id: r.event.rm_id,
      feature_flags_csv: r.event.feature_flags_csv,
      ysws_checks_enabled: r.event.ysws_checks_enabled,
      attendee_count: r.attendee_count,
      project_count: r.project_count,
      vote_count: r.vote_count,
    }));
  }

  async adminGetEvent(eventId: string, useRw = false) {
    const db = useRw ? this.dbRw : this.dbRo;
    const rows = await db
      .select({
        event: events,
        attendee_count: sql<number>`(SELECT count(*) FROM event_attendees WHERE event_attendees.event_id = "events"."id")`.mapWith(Number),
        project_count: sql<number>`(SELECT count(*) FROM projects WHERE projects.event_id = "events"."id")`.mapWith(Number),
        vote_count: sql<number>`(SELECT count(*) FROM votes WHERE votes.event_id = "events"."id")`.mapWith(Number),
      })
      .from(events)
      .where(eq(events.id, eventId))
      .limit(1);

    if (rows.length === 0) {
      throw new HttpException('Event not found', HttpStatus.NOT_FOUND);
    }
    const r = rows[0];
    return {
      ...mapEventPublic(r.event),
      owner_id: r.event.owner_id,
      poc_id: r.event.poc_id,
      rm_id: r.event.rm_id,
      feature_flags_csv: r.event.feature_flags_csv,
      ysws_checks_enabled: r.event.ysws_checks_enabled,
      attendee_count: r.attendee_count,
      project_count: r.project_count,
      vote_count: r.vote_count,
    };
  }

  async adminCreateEvent(
    data: {
      name: string;
      slug: string;
      description?: string;
      feature_flags_csv?: string;
      theme_name?: string;
      theme_background?: string;
      theme_font?: string;
      theme_primary?: string;
      theme_selected?: string;
      poc_id?: string | null;
      rm_id?: string | null;
    },
    user: User,
  ) {
    const existing = await this.dbRw.query.events.findFirst({
      where: eq(events.slug, data.slug),
    });
    if (existing) {
      throw new HttpException('Slug already in use', HttpStatus.CONFLICT);
    }

    const [event] = await this.dbRw
      .insert(events)
      .values({
        name: data.name,
        slug: data.slug,
        description: data.description || '',
        feature_flags_csv: data.feature_flags_csv || '',
        theme_name: data.theme_name || 'campfire',
        theme_background: data.theme_background || '',
        theme_font: data.theme_font || '"Ember& Fire", sans-serif',
        theme_primary: data.theme_primary || '#49B6F3',
        theme_selected: data.theme_selected || '#F59E0B',
        owner_id: user.id,
        poc_id: data.poc_id || null,
        rm_id: data.rm_id || null,
      })
      .returning();

    return this.adminGetEvent(event.id, true);
  }

  async adminUpdateEvent(
    eventId: string,
    data: Record<string, any>,
  ) {
    const event = await this.dbRw.query.events.findFirst({
      where: eq(events.id, eventId),
    });
    if (!event) {
      throw new HttpException('Event not found', HttpStatus.NOT_FOUND);
    }

    const allowedFields = [
      'name', 'slug', 'description', 'enabled', 'votable', 'voting_closed', 'leaderboard_enabled',
      'demo_links_optional', 'ysws_checks_enabled', 'feature_flags_csv',
      'theme_name', 'theme_background', 'theme_font', 'theme_primary', 'theme_selected',
      'poc_id', 'rm_id',
    ];

    const updateData: Record<string, any> = {};
    for (const [key, value] of Object.entries(data)) {
      if (allowedFields.includes(key) && value !== undefined) {
        updateData[key] = value;
      }
    }

    // Campfire events always have demo_links_optional forced on
    if (getFeatureFlagsList(event).includes('campfire')) {
      delete updateData['demo_links_optional'];
    }

    const stageFields = ['enabled', 'votable', 'voting_closed', 'leaderboard_enabled'];
    const hasStageChange = stageFields.some((f) => f in updateData);

    if (Object.keys(updateData).length > 0) {
      await this.dbRw
        .update(events)
        .set(updateData)
        .where(eq(events.id, eventId));
    }

    const result = await this.adminGetEvent(eventId, true);

    // Notify all SSE subscribers when stage flags change
    if (hasStageChange) {
      this.stageChange$.next({
        eventId,
        data: {
          enabled: result.enabled,
          votable: result.votable,
          voting_closed: result.voting_closed,
          leaderboard_enabled: result.leaderboard_enabled,
        },
      });
    }

    return result;
  }

  async adminDeleteEvent(eventId: string, user: User) {
    const event = await this.dbRw.query.events.findFirst({
      where: eq(events.id, eventId),
    });
    if (!event) {
      throw new HttpException('Event not found', HttpStatus.NOT_FOUND);
    }

    // POC/RM cannot delete events
    if (
      !user.is_superadmin &&
      (event.poc_id === user.id || event.rm_id === user.id)
    ) {
      throw new ForbiddenException('POC/RM cannot delete events');
    }

    if (
      getFeatureFlagsList(event).includes('campfire') &&
      !user.is_superadmin
    ) {
      throw new ForbiddenException(
        'Only superadmins can delete campfire events',
      );
    }

    // Delete related data first
    await this.dbRw.execute(
      sql`DELETE FROM votes WHERE event_id = ${eventId}`,
    );
    await this.dbRw.execute(
      sql`DELETE FROM project_collaborators WHERE project_id IN (SELECT id FROM projects WHERE event_id = ${eventId})`,
    );
    await this.dbRw.execute(
      sql`DELETE FROM projects WHERE event_id = ${eventId}`,
    );
    await this.dbRw.execute(
      sql`DELETE FROM event_attendees WHERE event_id = ${eventId}`,
    );
    await this.dbRw.execute(
      sql`DELETE FROM referrals WHERE event_id = ${eventId}`,
    );
    await this.dbRw.delete(events).where(eq(events.id, eventId));

    return { message: 'Event deleted' };
  }

  async adminGetAttendees(eventId: string) {
    const [attendeeRows, ownerRows, collabRows] = await Promise.all([
      this.dbRo.query.eventAttendees.findMany({
        where: eq(eventAttendees.event_id, eventId),
        with: { user: true },
      }),
      this.dbRo
        .select({ owner_id: projects.owner_id })
        .from(projects)
        .where(eq(projects.event_id, eventId)),
      this.dbRo
        .select({ user_id: projectCollaborators.user_id })
        .from(projectCollaborators)
        .innerJoin(projects, eq(projects.id, projectCollaborators.project_id))
        .where(eq(projects.event_id, eventId)),
    ]);

    const shippedIds = new Set([
      ...ownerRows.map((r) => r.owner_id),
      ...collabRows.map((r) => r.user_id),
    ]);

    return attendeeRows
      .filter((row) => row.user)
      .map((row) => ({
        id: row.id,
        user_id: row.user.id,
        email: row.user.email,
        display_name: row.user.display_name,
        has_project: shippedIds.has(row.user.id),
      }));
  }

  async adminAddAttendee(eventId: string, email: string) {
    const event = await this.dbRw.query.events.findFirst({
      where: eq(events.id, eventId),
    });
    if (!event) {
      throw new HttpException('Event not found', HttpStatus.NOT_FOUND);
    }

    const emailLower = email.trim().toLowerCase();
    let user = await this.dbRw.query.users.findFirst({
      where: eq(users.email, emailLower),
    });

    if (!user) {
      const localPart = emailLower.split('@')[0];
      const [created] = await this.dbRw
        .insert(users)
        .values({
          email: emailLower,
          first_name: localPart,
          last_name: '',
          display_name: '',
        })
        .returning();
      user = created;
    }

    const existing = await this.dbRw.query.eventAttendees.findFirst({
      where: and(
        eq(eventAttendees.event_id, eventId),
        eq(eventAttendees.user_id, user.id),
      ),
    });

    if (existing) {
      throw new HttpException(
        'User is already attending this event',
        HttpStatus.CONFLICT,
      );
    }

    await this.dbRw.insert(eventAttendees).values({
      event_id: eventId,
      user_id: user.id,
    });

    return {
      id: user.id,
      user_id: user.id,
      email: user.email,
      display_name: user.display_name,
      has_project: false,
    };
  }

  async adminRemoveAttendee(eventId: string, userId: string, caller: User) {
    // Only RM, owner, admins, and superadmins can remove attendees — not POC
    if (!caller.is_superadmin && !caller.is_admin) {
      const event = await this.dbRw.query.events.findFirst({
        where: eq(events.id, eventId),
        columns: { owner_id: true, rm_id: true, poc_id: true },
      });
      if (!event) {
        throw new HttpException('Event not found', HttpStatus.NOT_FOUND);
      }
      const isPocOnly =
        event.poc_id === caller.id &&
        event.owner_id !== caller.id &&
        event.rm_id !== caller.id;
      if (isPocOnly) {
        throw new ForbiddenException('POCs cannot remove attendees');
      }
    }

    await this.dbRw
      .delete(eventAttendees)
      .where(
        and(
          eq(eventAttendees.event_id, eventId),
          eq(eventAttendees.user_id, userId),
        ),
      );
    return { message: 'Attendee removed' };
  }

  async adminGetEventStats(eventId: string) {
    const [attendeeRows, projectRows, collabRows] = await Promise.all([
      this.dbRo.query.eventAttendees.findMany({
        where: eq(eventAttendees.event_id, eventId),
        with: { user: true },
      }),
      // Use SQL COUNT for vote counts instead of loading all vote rows
      this.dbRo
        .select({
          id: projects.id,
          name: projects.name,
          image_url: projects.image_url,
          description: projects.description,
          owner_id: projects.owner_id,
          vote_count: sql<number>`(SELECT count(*) FROM votes WHERE votes.project_id = "projects"."id")`.mapWith(Number),
        })
        .from(projects)
        .where(eq(projects.event_id, eventId)),
      this.dbRo.query.projectCollaborators.findMany({
        where: inArray(
          projectCollaborators.project_id,
          sql`(SELECT id FROM projects WHERE event_id = ${eventId})`,
        ),
        columns: { user_id: true },
      }),
    ]);

    // Build a set of user IDs who have submitted a project (as owner or collaborator)
    const usersWithProject = new Set<string>();
    for (const p of projectRows) {
      usersWithProject.add(p.owner_id);
    }
    for (const c of collabRows) {
      usersWithProject.add(c.user_id);
    }

    const attendees = attendeeRows.map((row) => ({
      user_id: row.user.id,
      email: row.user.email,
      display_name: row.user.display_name,
      has_project: usersWithProject.has(row.user.id),
    }));

    const leaderboard = projectRows
      .map((p) => ({
        id: p.id,
        name: p.name,
        image_url: p.image_url,
        description: p.description,
        owner_id: p.owner_id,
        vote_count: p.vote_count,
      }))
      .sort((a, b) => b.vote_count - a.vote_count);

    const submitted = attendees.filter((a) => a.has_project).length;

    return {
      total_attendees: attendees.length,
      submitted_count: submitted,
      missing_count: attendees.length - submitted,
      attendees,
      leaderboard,
    };
  }

  async adminGetLeaderboard(eventId: string) {
    const event = await this.dbRo.query.events.findFirst({
      where: eq(events.id, eventId),
      columns: { feature_flags_csv: true },
    });
    const isFlagship = event ? getFeatureFlagsList(event).includes('flagship') : false;

    const rows = await this.dbRo
      .select({
        id: projects.id,
        name: projects.name,
        repo: projects.repo,
        image_url: projects.image_url,
        demo: projects.demo,
        description: projects.description,
        hours_spent: projects.hours_spent,
        owner_id: projects.owner_id,
        owner_name: users.display_name,
        vote_count: sql<number>`(SELECT count(*) FROM votes WHERE votes.project_id = "projects"."id")`.mapWith(Number),
        manual_points: projects.manual_points,
      })
      .from(projects)
      .innerJoin(users, eq(projects.owner_id, users.id))
      .where(eq(projects.event_id, eventId));

    // Fetch collaborators for all projects in one query
    const projectIds = rows.map((r) => r.id);
    const collabRows = projectIds.length
      ? await this.dbRo
          .select({
            project_id: projectCollaborators.project_id,
            user_id: users.id,
            display_name: users.display_name,
          })
          .from(projectCollaborators)
          .innerJoin(users, eq(projectCollaborators.user_id, users.id))
          .where(inArray(projectCollaborators.project_id, projectIds))
      : [];

    const collabsByProject = new Map<string, { user_id: string; display_name: string }[]>();
    for (const c of collabRows) {
      const list = collabsByProject.get(c.project_id) ?? [];
      list.push({ user_id: c.user_id, display_name: c.display_name });
      collabsByProject.set(c.project_id, list);
    }

    const result = rows
      .map((p) => ({
        ...p,
        points: isFlagship ? p.manual_points : p.vote_count,
        collaborators: collabsByProject.get(p.id) ?? [],
      }))
      .sort((a, b) => (isFlagship ? b.manual_points - a.manual_points : b.vote_count - a.vote_count));

    return result;
  }

  async adminSetProjectPoints(eventId: string, projectId: string, points: number) {
    const [event, project] = await Promise.all([
      this.dbRw.query.events.findFirst({
        where: eq(events.id, eventId),
        columns: { id: true, feature_flags_csv: true },
      }),
      this.dbRw.query.projects.findFirst({
        where: and(eq(projects.id, projectId), eq(projects.event_id, eventId)),
        columns: { id: true },
      }),
    ]);

    if (!event) {
      throw new HttpException('Event not found', HttpStatus.NOT_FOUND);
    }
    if (!getFeatureFlagsList(event).includes('flagship')) {
      throw new ForbiddenException('Manual points are only available for flagship events');
    }
    if (!project) {
      throw new HttpException('Project not found in this event', HttpStatus.NOT_FOUND);
    }

    await this.dbRw
      .update(projects)
      .set({ manual_points: points })
      .where(eq(projects.id, projectId));

    return { message: 'Points updated' };
  }

  // ── Campfire Dashboard (superadmin) ────────────────────────────────

  async getCampfireDashboard() {
    // Check Redis cache first
    try {
      const cached = await this.redis.get(EventsService.DASHBOARD_CACHE_KEY);
      if (cached) return JSON.parse(cached);
    } catch {
      // Redis unavailable — fall through to live query
    }

    // Fetch all campfire events with counts in a single query
    const campfireRows = await this.dbR
      .select({
        event: events,
        attendee_count: sql<number>`(SELECT count(*) FROM event_attendees WHERE event_attendees.event_id = "events"."id")`.mapWith(Number),
        project_count: sql<number>`(SELECT count(*) FROM projects WHERE projects.event_id = "events"."id")`.mapWith(Number),
        shipper_count: sql<number>`(
          SELECT count(DISTINCT u) FROM (
            SELECT owner_id AS u FROM projects WHERE projects.event_id = "events"."id"
            UNION
            SELECT pc.user_id AS u FROM project_collaborators pc
              JOIN projects p ON pc.project_id = p.id
              WHERE p.event_id = "events"."id"
          ) sub
        )`.mapWith(Number),
      })
      .from(events);

    // Filter to campfire events in JS, excluding flagship and disabled events
    const campfireEvents = campfireRows.filter((r) => {
      const flags = getFeatureFlagsList(r.event);
      return flags.includes('campfire') && !flags.includes('flagship') && r.event.enabled;
    });

    if (campfireEvents.length === 0) {
      return {
        total_shippers: 0,
        total_projects: 0,
        total_attendees: 0,
        total_checkins: 0,
        total_scanned_either_day: 0,
        events: [],
      };
    }

    const eventIds = campfireEvents.map((r) => r.event.id);

    // Count unique users who shipped (owners + collaborators) across all campfire events
    const idList = sql.join(eventIds.map((id) => sql`${id}`), sql`, `);
    const [shipperRow] = await this.dbR
      .select({
        count: sql<number>`(
          SELECT count(DISTINCT u) FROM (
            SELECT owner_id AS u FROM projects WHERE event_id IN (${idList})
            UNION
            SELECT pc.user_id AS u FROM project_collaborators pc
              JOIN projects p ON pc.project_id = p.id
              WHERE p.event_id IN (${idList})
          ) sub
        )`.mapWith(Number),
      })
      .from(sql`(SELECT 1) AS dummy`);

    // Fetch scan counts from Cockpit (cached, aggregate only — no PII exposed)
    const scanCountsBySlug = await this.getCockpitScanCounts();

    const totalShippers = shipperRow?.count ?? 0;
    const totalProjects = campfireEvents.reduce((s, r) => s + r.project_count, 0);
    const totalAttendees = campfireEvents.reduce((s, r) => s + r.attendee_count, 0);

    const eventsData = campfireEvents.map((r) => {
      const scan = scanCountsBySlug.get(r.event.slug);
      return {
        id: r.event.id,
        name: r.event.name,
        slug: r.event.slug,
        attendee_count: r.attendee_count,
        project_count: r.project_count,
        shipper_count: r.shipper_count,
        ship_rate: (scan?.scanned_either_day_count ?? 0) > 0
          ? Math.round((r.shipper_count / (scan?.scanned_either_day_count ?? 0)) * 1000) / 10
          : 0,
        checkin_count: scan?.checkin_count ?? 0,
        scanned_day1_count: scan?.scanned_day1_count ?? 0,
        scanned_day2_count: scan?.scanned_day2_count ?? 0,
        scanned_either_day_count: scan?.scanned_either_day_count ?? 0,
      };
    });

    // Sort by ship rate descending for "best performing"
    eventsData.sort((a, b) => b.ship_rate - a.ship_rate);

    const totalCheckins = eventsData.reduce((s, e) => s + e.checkin_count, 0);
    const totalScannedEitherDay = eventsData.reduce((s, e) => s + e.scanned_either_day_count, 0);

    const result = {
      total_shippers: totalShippers,
      total_projects: totalProjects,
      total_attendees: totalAttendees,
      total_checkins: totalCheckins,
      total_scanned_either_day: totalScannedEitherDay,
      events: eventsData,
    };

    // Cache in Redis for 5 minutes
    try {
      await this.redis.set(
        EventsService.DASHBOARD_CACHE_KEY,
        JSON.stringify(result),
        'EX',
        EventsService.DASHBOARD_CACHE_TTL,
      );
    } catch {
      // Redis unavailable — continue without caching
    }

    return result;
  }

  // ── Public Dashboard (no auth, numbers + event names only) ─────────

  async getPublicDashboard() {
    const dashboard = await this.getCampfireDashboard();

    return {
      total_shippers: dashboard.total_shippers,
      total_projects: dashboard.total_projects,
      total_attendees: dashboard.total_attendees,
      total_checkins: dashboard.total_checkins,
      total_scanned_either_day: dashboard.total_scanned_either_day,
      events: dashboard.events.map((e: any) => ({
        name: e.name,
        slug: e.slug,
        attendee_count: e.attendee_count,
        project_count: e.project_count,
        shipper_count: e.shipper_count,
        ship_rate: e.ship_rate,
        checkin_count: e.checkin_count,
        scanned_day1_count: e.scanned_day1_count,
        scanned_day2_count: e.scanned_day2_count,
        scanned_either_day_count: e.scanned_either_day_count,
      })),
    };
  }

  // ── Campfire (superadmin) methods ───────────────────────────────────

  private assertSuperadmin(user: User) {
    if (!user.is_superadmin) {
      throw new ForbiddenException('Superadmin access required');
    }
    if (!this.cockpitApiKey) {
      throw new HttpException('Cockpit API key not configured', HttpStatus.INTERNAL_SERVER_ERROR);
    }
  }

  /**
   * Returns cached Cockpit scan counts (slug → aggregate counts).
   * Refreshes at most once every 2 minutes. Concurrent callers share the same fetch.
   */
  private async getCockpitScanCounts(): Promise<
    Map<string, { checkin_count: number; scanned_day1_count: number; scanned_day2_count: number; scanned_either_day_count: number }>
  > {
    const now = Date.now();
    if (this.cockpitScanCache && now - this.cockpitScanCache.fetchedAt < EventsService.SCAN_CACHE_TTL_MS) {
      return this.cockpitScanCache.data;
    }

    if (!this.cockpitApiKey) return new Map();

    // Coalesce concurrent requests into a single fetch
    if (!this.cockpitScanCachePromise) {
      this.cockpitScanCachePromise = (async () => {
        try {
          const cockpitEvents = await this.cockpitFetch('/events');
          const results = new Map<string, { checkin_count: number; scanned_day1_count: number; scanned_day2_count: number; scanned_either_day_count: number }>();

          const fetches = cockpitEvents.map(async (ce: any) => {
            try {
              const data = await this.cockpitFetch(
                `/events/${encodeURIComponent(ce.id)}/participants`,
              );
              const participants: any[] = data.participants || [];
              let checkins = 0;
              let day1 = 0;
              let day2 = 0;
              let eitherDay = 0;
              for (const p of participants) {
                if (p.isVolunteer) continue;
                if (p.checkinCompleted) checkins++;
                const s1 = !!p.scanned;
                const s2 = !!p.scannedDay2;
                if (s1) day1++;
                if (s2) day2++;
                if (s1 || s2) eitherDay++;
              }
              results.set(this.cockpitSlug(ce), {
                checkin_count: checkins,
                scanned_day1_count: day1,
                scanned_day2_count: day2,
                scanned_either_day_count: eitherDay,
              });
            } catch {
              // Skip individual event on error
            }
          });
          await Promise.all(fetches);

          this.cockpitScanCache = { data: results, fetchedAt: Date.now() };
        } catch {
          // Cockpit entirely unavailable — cache empty map so we don't retry immediately
          this.cockpitScanCache = { data: new Map(), fetchedAt: Date.now() };
        } finally {
          this.cockpitScanCachePromise = null;
        }
      })();
    }

    await this.cockpitScanCachePromise;
    return this.cockpitScanCache?.data ?? new Map();
  }

  private async cockpitFetch(path: string) {
    const res = await fetch(`https://cockpit.hackclub.com/api/v1${path}`, {
      headers: { 'Accept': '*/*', 'X-API-Key': this.cockpitApiKey },
    });
    if (!res.ok) {
      throw new HttpException(`Cockpit API error: ${res.status}`, HttpStatus.BAD_GATEWAY);
    }
    return res.json();
  }

  async getCampfireEvents(user: User) {
    this.assertSuperadmin(user);

    const cockpitEvents = await this.cockpitFetch('/events');

    const podiumEvents = await this.dbRo.query.events.findMany();
    const importedSlugs = new Set(podiumEvents.map((e) => e.slug));

    return cockpitEvents.map((ce: any) => ({
      ...ce,
      already_imported: importedSlugs.has(this.cockpitSlug(ce)),
    }));
  }

  async importCampfireEvent(cockpitEventId: string, user: User) {
    this.assertSuperadmin(user);

    const data = await this.cockpitFetch(
      `/events/${encodeURIComponent(cockpitEventId)}/participants`,
    );
    const cockpitEvent = data.event;
    const participants: any[] = data.participants || [];

    const slug = this.cockpitSlug(cockpitEvent);

    const existing = await this.dbRw.query.events.findFirst({
      where: eq(events.slug, slug),
    });
    if (existing) {
      throw new HttpException('Event already imported', HttpStatus.CONFLICT);
    }

    // Set up RM/POC as admins and track their user IDs
    const adminEmails = this.collectAdminEmails(cockpitEvent);
    let ownerId = user.id;
    for (const email of adminEmails) {
      const adminUser = await this.findOrCreateCockpitUser({ email });
      if (!adminUser.is_admin) {
        await this.dbRw
          .update(users)
          .set({ is_admin: true })
          .where(eq(users.id, adminUser.id));
      }
      if (ownerId === user.id) {
        ownerId = adminUser.id;
      }
    }

    const { pocId, rmId } = await this.resolvePocRmIds(cockpitEvent);

    // Create the Podium event (enable if Cockpit status is Active)
    const isActive = !cockpitEvent.status || cockpitEvent.status === 'Active';
    const [event] = await this.dbRw
      .insert(events)
      .values({
        name: cockpitEvent.displayName || `Campfire ${cockpitEvent.name}`,
        slug,
        description: `${cockpitEvent.format || ''} event in ${cockpitEvent.city || cockpitEvent.country || 'TBD'}`.trim(),
        feature_flags_csv: 'campfire',
        theme_name: 'campfire',
        enabled: isActive,
        owner_id: ownerId,
        poc_id: pocId,
        rm_id: rmId,
      })
      .returning();

    // Import participants with full data
    const importedCount = await this.syncParticipants(event.id, participants);

    return {
      message: 'Event imported successfully',
      event_id: event.id,
      slug: event.slug,
      attendees_imported: importedCount,
      admins: Array.from(adminEmails),
    };
  }

  async syncCampfireEvent(cockpitEventId: string, user: User) {
    this.assertSuperadmin(user);

    const data = await this.cockpitFetch(
      `/events/${encodeURIComponent(cockpitEventId)}/participants`,
    );
    const cockpitEvent = data.event;
    const participants: any[] = data.participants || [];

    const slug = this.cockpitSlug(cockpitEvent);

    const existing = await this.dbRw.query.events.findFirst({
      where: eq(events.slug, slug),
    });
    if (!existing) {
      throw new HttpException('Event not found in Podium — import it first', HttpStatus.NOT_FOUND);
    }

    // If cockpit event is no longer active, disable the Podium event
    if (cockpitEvent.status && cockpitEvent.status !== 'Active') {
      if (existing.enabled) {
        await this.dbRw
          .update(events)
          .set({ enabled: false })
          .where(eq(events.id, existing.id));
      }
      return {
        message: `Event disabled (Cockpit status: ${cockpitEvent.status})`,
        event_id: existing.id,
        slug: existing.slug,
        attendees_synced: 0,
        disabled: true,
        admins: [],
      };
    }

    // Ensure RM/POC are still admins
    const adminEmails = this.collectAdminEmails(cockpitEvent);
    for (const email of adminEmails) {
      const adminUser = await this.findOrCreateCockpitUser({ email });
      if (!adminUser.is_admin) {
        await this.dbRw
          .update(users)
          .set({ is_admin: true })
          .where(eq(users.id, adminUser.id));
      }
    }

    // Update POC/RM IDs on the event and ensure enabled for active events
    const { pocId, rmId } = await this.resolvePocRmIds(cockpitEvent);
    await this.dbRw
      .update(events)
      .set({ poc_id: pocId, rm_id: rmId, enabled: true })
      .where(eq(events.id, existing.id));

    // Sync participants non-destructively (add new, update existing user data, never remove)
    const syncedCount = await this.syncParticipants(existing.id, participants);

    return {
      message: 'Event synced successfully',
      event_id: existing.id,
      slug: existing.slug,
      attendees_synced: syncedCount,
      admins: Array.from(adminEmails),
    };
  }

  async syncCampfireEventByPodiumId(podiumEventId: string) {
    if (!this.cockpitApiKey) {
      throw new HttpException('Cockpit API key not configured', HttpStatus.INTERNAL_SERVER_ERROR);
    }

    const podiumEvent = await this.dbRw.query.events.findFirst({
      where: eq(events.id, podiumEventId),
    });
    if (!podiumEvent) {
      throw new HttpException('Event not found', HttpStatus.NOT_FOUND);
    }
    if (!getFeatureFlagsList(podiumEvent).includes('campfire')) {
      throw new HttpException('This event is not a Campfire event', HttpStatus.BAD_REQUEST);
    }

    // Find matching cockpit event by slug
    const cockpitEvents = await this.cockpitFetch('/events');
    const match = cockpitEvents.find(
      (ce: any) => this.cockpitSlug(ce) === podiumEvent.slug,
    );
    if (!match) {
      throw new HttpException('No matching Cockpit event found', HttpStatus.NOT_FOUND);
    }

    // If cockpit event is no longer active, disable the Podium event
    if (match.status !== 'Active') {
      if (podiumEvent.enabled) {
        await this.dbRw
          .update(events)
          .set({ enabled: false })
          .where(eq(events.id, podiumEvent.id));
      }
      return {
        message: `Event disabled (Cockpit status: ${match.status})`,
        event_id: podiumEvent.id,
        attendees_synced: 0,
        disabled: true,
      };
    }

    // Fetch participants
    const data = await this.cockpitFetch(
      `/events/${encodeURIComponent(match.id)}/participants`,
    );
    const cockpitEvent = data.event;
    const participants: any[] = data.participants || [];

    // Ensure RM/POC users exist and are admins
    const adminEmails = this.collectAdminEmails(cockpitEvent);
    for (const email of adminEmails) {
      const adminUser = await this.findOrCreateCockpitUser({ email });
      if (!adminUser.is_admin) {
        await this.dbRw
          .update(users)
          .set({ is_admin: true })
          .where(eq(users.id, adminUser.id));
      }
    }

    // Update POC/RM IDs on the event and ensure enabled for active events
    const { pocId, rmId } = await this.resolvePocRmIds(cockpitEvent);
    await this.dbRw
      .update(events)
      .set({ poc_id: pocId, rm_id: rmId, enabled: true })
      .where(eq(events.id, podiumEvent.id));

    // Sync participants non-destructively
    const syncedCount = await this.syncParticipants(podiumEvent.id, participants);

    return {
      message: 'Event synced successfully',
      event_id: podiumEvent.id,
      attendees_synced: syncedCount,
    };
  }

  async syncAllCampfireEvents(user: User) {
    this.assertSuperadmin(user);

    const cockpitEvents = await this.cockpitFetch('/events');
    const podiumEvents = await this.dbRo.query.events.findMany();
    const slugToEvent = new Map(podiumEvents.map((e) => [e.slug, e]));

    // Only sync events that are already imported
    const toSync = cockpitEvents.filter(
      (ce: any) => slugToEvent.has(this.cockpitSlug(ce)),
    );

    const results: { id: string; name: string; synced: number; disabled?: boolean; error?: string }[] = [];

    for (const ce of toSync) {
      try {
        // If cockpit event is no longer active, disable the Podium event
        if (ce.status !== 'Active') {
          const podiumEvent = slugToEvent.get(this.cockpitSlug(ce))!;
          if (podiumEvent.enabled) {
            await this.dbRw
              .update(events)
              .set({ enabled: false })
              .where(eq(events.id, podiumEvent.id));
          }
          results.push({
            id: ce.id,
            name: ce.displayName || ce.name,
            synced: 0,
            disabled: true,
          });
          continue;
        }

        const result = await this.syncCampfireEvent(ce.id, user);
        results.push({
          id: ce.id,
          name: ce.displayName || ce.name,
          synced: result.attendees_synced,
        });
      } catch (err: any) {
        results.push({
          id: ce.id,
          name: ce.displayName || ce.name,
          synced: 0,
          error: err.message || 'Unknown error',
        });
      }
    }

    const disabledCount = results.filter((r) => r.disabled).length;
    return {
      message: `Synced ${results.length} events${disabledCount > 0 ? ` (${disabledCount} disabled)` : ''}`,
      results,
    };
  }

  async importAllActiveCampfireEvents(user: User) {
    this.assertSuperadmin(user);

    const cockpitEvents = await this.cockpitFetch('/events');
    const podiumEvents = await this.dbRo.query.events.findMany();
    const importedSlugs = new Set(podiumEvents.map((e) => e.slug));

    // Only import active events that haven't been imported yet
    const toImport = cockpitEvents.filter(
      (ce: any) => ce.status === 'Active' && !importedSlugs.has(this.cockpitSlug(ce)),
    );

    const results: { id: string; name: string; imported: number; error?: string }[] = [];

    for (const ce of toImport) {
      try {
        const result = await this.importCampfireEvent(ce.id, user);
        results.push({
          id: ce.id,
          name: ce.displayName || ce.name,
          imported: result.attendees_imported,
        });
      } catch (err: any) {
        results.push({
          id: ce.id,
          name: ce.displayName || ce.name,
          imported: 0,
          error: err.message || 'Unknown error',
        });
      }
    }

    return {
      message: `Imported ${results.filter((r) => !r.error).length} of ${toImport.length} active events`,
      results,
    };
  }

  /** Add new participants as attendees and update user data. Never removes existing attendees. */
  private async syncParticipants(eventId: string, participants: any[]): Promise<number> {
    const validParticipants = participants.filter((p) => p.email);
    if (validParticipants.length === 0) return 0;

    // 1. Bulk upsert all users
    const userIds = await this.bulkUpsertCockpitUsers(validParticipants);

    // 2. Get existing attendees for this event in one query
    const existingAttendees = await this.dbRw.query.eventAttendees.findMany({
      where: eq(eventAttendees.event_id, eventId),
      columns: { user_id: true },
    });
    const existingUserIds = new Set(existingAttendees.map((a) => a.user_id));

    // 3. Bulk insert new attendees
    const newAttendees = userIds
      .filter((uid) => uid && !existingUserIds.has(uid))
      .map((uid) => ({ event_id: eventId, user_id: uid }));

    if (newAttendees.length > 0) {
      // Insert in batches of 500 to avoid query size limits
      for (let i = 0; i < newAttendees.length; i += 500) {
        const batch = newAttendees.slice(i, i + 500);
        await this.dbRw
          .insert(eventAttendees)
          .values(batch)
          .onConflictDoNothing();
      }
    }

    return newAttendees.length;
  }

  private cockpitSlug(cockpitEvent: any): string {
    const displayName = (cockpitEvent.displayName || '').trim();
    // Strip "Campfire" prefix to get the city name (e.g. "Campfire Miami" → "miami")
    const stripped = displayName.replace(/^campfire\s*/i, '').trim();
    if (!stripped) return `campfire-${cockpitEvent.id}`;
    return stripped.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
  }

  private async resolvePocRmIds(cockpitEvent: any): Promise<{ pocId: string | null; rmId: string | null }> {
    let pocId: string | null = null;
    let rmId: string | null = null;
    const pocEmails: string[] = (cockpitEvent.pocEmail || []).filter(Boolean).map((e: string) => e.trim().toLowerCase());
    const rmEmails: string[] = (cockpitEvent.rmEmail || []).filter(Boolean).map((e: string) => e.trim().toLowerCase());
    if (pocEmails.length > 0) {
      const pocUser = await this.dbRw.query.users.findFirst({
        where: eq(users.email, pocEmails[0]),
      });
      if (pocUser) pocId = pocUser.id;
    }
    if (rmEmails.length > 0) {
      const rmUser = await this.dbRw.query.users.findFirst({
        where: eq(users.email, rmEmails[0]),
      });
      if (rmUser) rmId = rmUser.id;
    }
    return { pocId, rmId };
  }

  private collectAdminEmails(cockpitEvent: any): Set<string> {
    const emails = new Set<string>();
    for (const e of [...(cockpitEvent.rmEmail || []), ...(cockpitEvent.pocEmail || [])]) {
      if (e) emails.add(e.trim().toLowerCase());
    }
    return emails;
  }

  private cockpitUserData(participant: any) {
    const s = (v: any, max: number) => ((v as string) || '').slice(0, max);
    const emailLower = (participant.email as string).trim().toLowerCase();
    return {
      email: emailLower,
      display_name: s(participant.displayName, 255),
      first_name: s(participant.legalFirstName, 50) || s(participant.displayName, 50) || emailLower.split('@')[0].slice(0, 50),
      last_name: s(participant.legalLastName, 50),
      phone: s(participant.phone, 20),
      street_1: s(participant.addressLine1, 255),
      street_2: s(participant.addressLine2, 255),
      city: s(participant.addressCity, 100),
      state: s(participant.addressState, 100),
      zip_code: s(participant.addressZip, 20),
      country: s(participant.addressCountry, 100),
      dob: (participant.dateOfBirth as string) || null,
    };
  }

  /**
   * Bulk upsert users from Cockpit participants.
   * Inserts new users; for existing users, fills in empty fields only.
   * Returns array of user IDs in same order as input.
   */
  private async bulkUpsertCockpitUsers(participants: any[]): Promise<string[]> {
    const allData = participants.map((p) => this.cockpitUserData(p));
    const emails = allData.map((d) => d.email);

    // 1. Fetch all existing users in one query
    const existingUsers = emails.length > 0
      ? await this.dbRw.query.users.findMany({
          where: inArray(users.email, emails),
        })
      : [];
    const existingByEmail = new Map(existingUsers.map((u) => [u.email, u]));

    // 2. Separate into new users and users needing updates
    const toInsert: typeof allData = [];
    const emailToIndex = new Map<string, number[]>();
    for (let i = 0; i < allData.length; i++) {
      const d = allData[i];
      // Track all indices for dedup
      if (!emailToIndex.has(d.email)) emailToIndex.set(d.email, []);
      emailToIndex.get(d.email)!.push(i);

      if (!existingByEmail.has(d.email) && !toInsert.some((t) => t.email === d.email)) {
        toInsert.push(d);
      }
    }

    // 3. Bulk insert new users (batches of 500)
    const newUsersByEmail = new Map<string, string>();
    for (let i = 0; i < toInsert.length; i += 500) {
      const batch = toInsert.slice(i, i + 500);
      const inserted = await this.dbRw
        .insert(users)
        .values(batch)
        .onConflictDoNothing()
        .returning({ id: users.id, email: users.email });
      for (const u of inserted) {
        newUsersByEmail.set(u.email, u.id);
      }
    }

    // 4. Batch update existing users that have empty fields (one UPDATE per field, using CASE)
    const fillableFields = [
      'display_name', 'first_name', 'last_name', 'phone',
      'street_1', 'street_2', 'city', 'state', 'zip_code', 'country',
    ] as const;

    const usersToUpdate: { id: string; updates: Record<string, string> }[] = [];
    for (const existing of existingUsers) {
      const data = allData.find((d) => d.email === existing.email);
      if (!data) continue;
      const updates: Record<string, string> = {};
      for (const field of fillableFields) {
        const cockpitVal = data[field];
        const existingVal = (existing as any)[field];
        if (cockpitVal && cockpitVal !== '' && (!existingVal || existingVal === '')) {
          updates[field] = cockpitVal;
        }
      }
      // Handle dob separately (nullable, not empty string)
      if (data.dob && !existing.dob) {
        updates['dob'] = data.dob;
      }
      if (Object.keys(updates).length > 0) {
        usersToUpdate.push({ id: existing.id, updates });
      }
    }

    // Run updates in parallel batches of 50
    for (let i = 0; i < usersToUpdate.length; i += 50) {
      const batch = usersToUpdate.slice(i, i + 50);
      await Promise.all(
        batch.map((u) =>
          this.dbRw.update(users).set(u.updates).where(eq(users.id, u.id)),
        ),
      );
    }

    // 5. Build result array mapping email → user ID
    const result: string[] = [];
    for (const d of allData) {
      const existing = existingByEmail.get(d.email);
      if (existing) {
        result.push(existing.id);
      } else {
        result.push(newUsersByEmail.get(d.email)!);
      }
    }

    return result;
  }

  /**
   * Find or create a single Cockpit user. Used for admin email lookups
   * where we need the full user object back.
   */
  private async findOrCreateCockpitUser(participant: any) {
    const data = this.cockpitUserData(participant);

    let user = await this.dbRw.query.users.findFirst({
      where: eq(users.email, data.email),
    });

    if (!user) {
      const [created] = await this.dbRw
        .insert(users)
        .values(data)
        .returning();
      user = created;
    }

    return user;
  }

  // ── Airtable sync methods ──────────────────────────────────────────

  private assertAirtableConfigured() {
    if (!this.airtableApiKey) {
      throw new HttpException('Airtable API key not configured', HttpStatus.INTERNAL_SERVER_ERROR);
    }
    if (!this.airtableBaseId || !this.airtableTableId) {
      throw new HttpException('Airtable base/table not configured', HttpStatus.INTERNAL_SERVER_ERROR);
    }
  }

  private async airtableFetch(path: string, options: RequestInit = {}) {
    const res = await fetch(`https://api.airtable.com/v0/${this.airtableBaseId}${path}`, {
      ...options,
      headers: {
        'Authorization': `Bearer ${this.airtableApiKey}`,
        'Content-Type': 'application/json',
        ...(options.headers as Record<string, string> || {}),
      },
    });
    if (!res.ok) {
      const body = await res.text();
      throw new HttpException(`Airtable API error: ${res.status} ${body}`, HttpStatus.BAD_GATEWAY);
    }
    return res.json();
  }

  private buildAirtableRecords(allProjects: any[]): { fields: Record<string, any> }[] {
    const records: { fields: Record<string, any> }[] = [];
    for (const p of allProjects) {
      const participants = [
        p.owner,
        ...p.collaborators.map((c: any) => c.user),
      ];

      for (const u of participants) {
        const fields: Record<string, any> = {
          'fldM8dvaeqsnZzSGj': p.repo || '',                    // Code URL
          'fldpIJmCQu1YcqIIo': p.demo || '',                    // Playable URL
          'fldMtDgBFPPtLZhaW': u.first_name || '',              // First Name
          'fldPUsofPv5qCyNz2': u.last_name || '',               // Last Name
          'fldnzPNUA9MITRwVd': u.email,                         // Email
          'fld6Ftv1uIi6hGeiK': p.description || '',             // Description
          'fldpfhr4TzdnzrJLQ': u.street_1 || '',                // Address (Line 1)
          'fldNmlSPKvYzRysIj': u.street_2 || '',                // Address (Line 2)
          'fldVisMSOsoUiMt0d': u.city || '',                    // City
          'flddqf2FyQiaCFu01': u.state || '',                   // State / Province
          'fldlmKpglzyJ6F5hQ': u.country || '',                 // Country
          'fldojg2Bhx7GMW1Ch': u.zip_code || '',                // ZIP / Postal Code
          'fldg5wAWQzC2FMZaO': p.hours_spent || 0,              // Optional - Override Hours Spent
        };

        // Birthday (date field, needs ISO format)
        if (u.dob) {
          fields['fldCTWBJ4H7rvQdVq'] = u.dob;
        }

        // Screenshot attachment
        if (p.image_url) {
          fields['fldY9H3WlDPE0k1rK'] = [{ url: p.image_url }];
        }

        records.push({ fields });
      }
    }
    return records;
  }

  private async batchUpsertToAirtable(records: { fields: Record<string, any> }[]) {
    const BATCH_SIZE = 10;
    const DELAY_MS = 220; // ~4.5 req/sec to stay under the 5 req/sec limit
    let synced = 0;
    const errors: string[] = [];

    for (let i = 0; i < records.length; i += BATCH_SIZE) {
      const batch = records.slice(i, i + BATCH_SIZE);
      try {
        console.log('[airtable-sync] Sending batch', Math.floor(i / BATCH_SIZE) + 1, 'with', batch.length, 'records');
        await this.airtableFetch(`/${this.airtableTableId}`, {
          method: 'PATCH',
          body: JSON.stringify({
            records: batch,
            performUpsert: {
              fieldsToMergeOn: ['fldnzPNUA9MITRwVd'], // Email
            },
            typecast: true,
          }),
        });
        synced += batch.length;
        console.log('[airtable-sync] Batch succeeded, total synced:', synced);
      } catch (err: any) {
        console.error('[airtable-sync] Batch failed:', err.message);
        errors.push(`Batch ${Math.floor(i / BATCH_SIZE) + 1}: ${err.message}`);
      }

      // Rate limit delay between batches
      if (i + BATCH_SIZE < records.length) {
        await new Promise((resolve) => setTimeout(resolve, DELAY_MS));
      }
    }

    return { synced, total: records.length, errors };
  }

  async syncAllProjectsToAirtable(user: User) {
    this.assertSuperadmin(user);
    this.assertAirtableConfigured();

    console.log('[airtable-sync] Starting sync, airtableBaseId:', this.airtableBaseId, 'tableId:', this.airtableTableId);

    // Get campfire events that have voting closed
    const campfireEvents = await this.dbRo.query.events.findMany();
    const campfireEventIds = campfireEvents
      .filter((e) => e.feature_flags_csv.includes('campfire') && e.voting_closed)
      .map((e) => e.id);

    console.log('[airtable-sync] Found', campfireEventIds.length, 'campfire events with voting closed');

    if (campfireEventIds.length === 0) {
      return { message: 'No campfire events found', synced: 0 };
    }

    // Get all projects for campfire events with their owners, collaborators, and votes
    const allProjects = await this.dbRo.query.projects.findMany({
      where: inArray(projects.event_id, campfireEventIds),
      with: {
        owner: true,
        collaborators: { with: { user: true } },
        votes: true,
        event: true,
      },
    });

    console.log('[airtable-sync] Found', allProjects.length, 'projects to sync');

    if (allProjects.length === 0) {
      return { message: 'No projects to sync', synced: 0 };
    }

    const records = this.buildAirtableRecords(allProjects);
    console.log('[airtable-sync] Built', records.length, 'participant records from', allProjects.length, 'projects');

    const { synced, total, errors } = await this.batchUpsertToAirtable(records);

    const result = {
      message: `Synced ${synced} of ${total} participant records to Airtable`,
      synced,
      total,
      errors: errors.length > 0 ? errors : undefined,
    };
    console.log('[airtable-sync] Done:', JSON.stringify(result));
    return result;
  }

  async syncEventProjectsToAirtable(eventId: string, user: User) {
    this.assertSuperadmin(user);
    this.assertAirtableConfigured();

    const event = await this.dbRo.query.events.findFirst({
      where: eq(events.id, eventId),
    });
    if (!event) {
      throw new HttpException('Event not found', HttpStatus.NOT_FOUND);
    }

    console.log('[airtable-sync] Starting single-event sync for', event.name, '(', eventId, ')');

    const eventProjects = await this.dbRo.query.projects.findMany({
      where: eq(projects.event_id, eventId),
      with: {
        owner: true,
        collaborators: { with: { user: true } },
        votes: true,
        event: true,
      },
    });

    if (eventProjects.length === 0) {
      return { message: 'No projects to sync', synced: 0, total: 0 };
    }

    const records = this.buildAirtableRecords(eventProjects);
    console.log('[airtable-sync] Built', records.length, 'participant records from', eventProjects.length, 'projects');

    const { synced, total, errors } = await this.batchUpsertToAirtable(records);

    const result = {
      message: `Synced ${synced} of ${total} participant records to Airtable`,
      synced,
      total,
      errors: errors.length > 0 ? errors : undefined,
    };
    console.log('[airtable-sync] Done:', JSON.stringify(result));
    return result;
  }

  // ── Platform settings (superadmin) ─────────────────────────────────

  async getPlatformSettings() {
    return this.platformSettings.getAll();
  }

  async updatePlatformSettings(data: {
    github_validation_enabled?: boolean;
    itch_validation_enabled?: boolean;
  }) {
    if (data.github_validation_enabled !== undefined) {
      await this.platformSettings.set('github_validation_enabled', data.github_validation_enabled);
    }
    if (data.itch_validation_enabled !== undefined) {
      await this.platformSettings.set('itch_validation_enabled', data.itch_validation_enabled);
    }
    return this.platformSettings.getAll();
  }

  // ── Itch.io validation ─────────────────────────────────────────────

  async validateItchGames(user: User) {
    this.assertSuperadmin(user);

    // Get all campfire events
    const allEvents = await this.dbRo.query.events.findMany();
    const campfireEventIds = allEvents
      .filter((e) => e.feature_flags_csv.includes('campfire'))
      .map((e) => e.id);

    if (campfireEventIds.length === 0) {
      return { message: 'No campfire events found', results: [] };
    }

    // Get all projects with demo URLs for those events
    const allProjects = await this.dbRo.query.projects.findMany({
      where: inArray(projects.event_id, campfireEventIds),
      with: { event: true },
    });

    const withDemo = allProjects.filter((p) => p.demo && p.demo.trim());

    // Filter to itch.io URLs only
    const itchProjects = withDemo.filter((p) => {
      try {
        const host = new URL(p.demo).hostname;
        return host === 'itch.io' || host.endsWith('.itch.io');
      } catch {
        return false;
      }
    });

    console.log(
      `[itch-validate] ${itchProjects.length} itch.io links across ${campfireEventIds.length} campfire events`,
    );

    const DELAY_MS = 2000; // 2s between requests — well under itch.io limits
    const results: {
      project_id: string;
      project_name: string;
      event_slug: string;
      demo_url: string;
      playable: boolean;
      reason: string;
    }[] = [];

    for (let i = 0; i < itchProjects.length; i++) {
      const p = itchProjects[i];
      const { playable, reason } = await this.checkItchPlayable(p.demo);

      results.push({
        project_id: p.id,
        project_name: p.name,
        event_slug: (p as any).event?.slug ?? 'unknown',
        demo_url: p.demo,
        playable,
        reason,
      });

      console.log(
        `[itch-validate] [${i + 1}/${itchProjects.length}] ${p.name} — ${playable ? 'PLAYABLE' : 'NOT PLAYABLE'} (${reason})`,
      );

      // Rate limit — don't hammer itch.io
      if (i < itchProjects.length - 1) {
        await new Promise((resolve) => setTimeout(resolve, DELAY_MS));
      }
    }

    const playableCount = results.filter((r) => r.playable).length;
    const notPlayableCount = results.filter((r) => !r.playable).length;

    return {
      message: `Checked ${results.length} itch.io links: ${playableCount} playable, ${notPlayableCount} not playable`,
      total: results.length,
      playable: playableCount,
      not_playable: notPlayableCount,
      results,
    };
  }

  private async checkItchPlayable(
    url: string,
  ): Promise<{ playable: boolean; reason: string }> {
    try {
      const resp = await fetch(url, {
        headers: { 'User-Agent': 'Mozilla/5.0 (compatible; PodiumValidator/1.0)' },
        redirect: 'follow',
        signal: AbortSignal.timeout(15_000),
      });

      if (!resp.ok) {
        return { playable: false, reason: `HTTP ${resp.status}` };
      }

      const html = await resp.text();

      // .game_frame is the iframe wrapper itch.io uses for browser-playable games
      if (html.includes('class="game_frame"') || html.includes("class='game_frame'") || html.includes('id="game_drop"')) {
        return { playable: true, reason: 'playable' };
      }

      // Download-only pages have upload buttons
      if (html.includes('class="upload"') || html.includes("class='upload'")) {
        return { playable: false, reason: 'download-only (no browser embed)' };
      }

      return { playable: false, reason: 'no game_frame found' };
    } catch (err: any) {
      if (err?.name === 'TimeoutError' || err?.name === 'AbortError') {
        return { playable: false, reason: 'timeout' };
      }
      return { playable: false, reason: `error: ${err?.message ?? err}` };
    }
  }

  // ── Test methods ───────────────────────────────────────────────────

  async createTestEvent(name: string, description: string, user: User) {
    if (!this.enableTestEndpoints) {
      throw new HttpException('Not found', HttpStatus.NOT_FOUND);
    }
    if (!this.activeEventSeries) {
      throw new HttpException(
        'No active event series configured',
        HttpStatus.BAD_REQUEST,
      );
    }

    const slugify = (await import('slugify')).default;
    const crypto = await import('crypto');
    const baseSlug = slugify(name, { lower: true, strict: true }).slice(0, 40);
    const slug = `${baseSlug}-${crypto.randomBytes(4).toString('base64url')}`;

    const [event] = await this.dbRw
      .insert(events)
      .values({
        name,
        slug,
        description,
        owner_id: user.id,
        votable: true,
        leaderboard_enabled: true,
        demo_links_optional: true,
        feature_flags_csv: this.activeEventSeries,
      })
      .returning();

    return mapEventPublic({ ...event, projects: [] });
  }

  async cleanupTestData() {
    if (!this.enableTestEndpoints) {
      throw new HttpException('Not found', HttpStatus.NOT_FOUND);
    }

    const testUserFilter = sql`
      email LIKE 'test+pw%@example.com'
      OR email LIKE 'organizer+%@test.local'
      OR email LIKE 'attendee+%@test.local'
    `;

    await this.dbRw.execute(
      sql`DELETE FROM votes WHERE voter_id IN (SELECT id FROM users WHERE ${testUserFilter})`,
    );
    await this.dbRw.execute(
      sql`DELETE FROM votes WHERE project_id IN (SELECT id FROM projects WHERE owner_id IN (SELECT id FROM users WHERE ${testUserFilter}))`,
    );
    await this.dbRw.execute(
      sql`DELETE FROM project_collaborators WHERE user_id IN (SELECT id FROM users WHERE ${testUserFilter})`,
    );
    await this.dbRw.execute(
      sql`DELETE FROM projects WHERE owner_id IN (SELECT id FROM users WHERE ${testUserFilter})`,
    );
    await this.dbRw.execute(
      sql`DELETE FROM event_attendees WHERE user_id IN (SELECT id FROM users WHERE ${testUserFilter})`,
    );
    await this.dbRw.execute(
      sql`DELETE FROM events WHERE owner_id IN (SELECT id FROM users WHERE ${testUserFilter})`,
    );
    await this.dbRw.execute(
      sql`DELETE FROM referrals WHERE user_id IN (SELECT id FROM users WHERE ${testUserFilter})`,
    );
    await this.dbRw.execute(
      sql`DELETE FROM users WHERE ${testUserFilter}`,
    );

    return { message: 'Test data cleaned up' };
  }
}
