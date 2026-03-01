import { Inject, Injectable, HttpException, HttpStatus } from '@nestjs/common';
import { eq, and } from 'drizzle-orm';
import {
  DRIZZLE_RW,
  DRIZZLE_RO,
  DRIZZLE_R,
  type Database,
  type User,
  events,
  projects,
  votes,
  referrals,
  eventAttendees,
  getMaxVotesPerUser,
  BAD_ACCESS,
  PlatformSettingsService,
} from '@podium/shared';

@Injectable()
export class AdminService {
  constructor(
    @Inject(DRIZZLE_RW) private readonly dbRw: Database,
    @Inject(DRIZZLE_RO) private readonly dbRo: Database,
    @Inject(DRIZZLE_R) private readonly dbR: Database,
    private readonly platformSettings: PlatformSettingsService,
  ) {}

  private async getOwnedEvent(eventId: string, user: User) {
    const event = await this.dbRo.query.events.findFirst({
      where: eq(events.id, eventId),
      with: { projects: { with: { votes: true } } },
    });
    if (!event) {
      throw BAD_ACCESS;
    }
    if (user.is_superadmin) {
      return event;
    }
    if (
      event.owner_id === user.id ||
      event.poc_id === user.id ||
      event.rm_id === user.id
    ) {
      return event;
    }
    // Allow is_admin users who are attendees of this event
    if (user.is_admin) {
      const attendee = await this.dbRo.query.eventAttendees.findFirst({
        where: and(
          eq(eventAttendees.event_id, eventId),
          eq(eventAttendees.user_id, user.id),
        ),
      });
      if (attendee) {
        return event;
      }
    }
    throw BAD_ACCESS;
  }

  async getEventAdmin(eventId: string, user: User) {
    const event = await this.getOwnedEvent(eventId, user);

    const attendees = await this.dbRo.query.eventAttendees.findMany({
      where: eq(eventAttendees.event_id, eventId),
    });

    const voteCount = event.projects.reduce(
      (sum: number, p: any) => sum + (p.votes?.length ?? 0),
      0,
    );

    return {
      id: event.id,
      name: event.name,
      slug: event.slug,
      description: event.description,
      enabled: event.enabled,
      votable: event.votable,
      voting_closed: event.voting_closed,
      leaderboard_enabled: event.leaderboard_enabled,
      demo_links_optional: event.demo_links_optional,
      max_votes_per_user: getMaxVotesPerUser(),
      owner_id: event.owner_id,
      feature_flags_csv: event.feature_flags_csv,
      ysws_checks_enabled: event.ysws_checks_enabled,
      theme_name: event.theme_name,
      theme_background: event.theme_background,
      theme_font: event.theme_font,
      theme_primary: event.theme_primary,
      theme_selected: event.theme_selected,
      attendee_count: attendees.length,
      project_count: event.projects.length,
      vote_count: voteCount,
    };
  }

  async getEventAttendees(eventId: string, user: User) {
    await this.getOwnedEvent(eventId, user);

    const rows = await this.dbRo.query.eventAttendees.findMany({
      where: eq(eventAttendees.event_id, eventId),
      with: { user: true },
    });

    return rows.map((row) => ({
      id: row.user.id,
      email: row.user.email,
      display_name: row.user.display_name,
      first_name: row.user.first_name,
      last_name: row.user.last_name,
    }));
  }

  async removeAttendee(eventId: string, userId: string, user: User) {
    await this.getOwnedEvent(eventId, user);

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

  async getEventLeaderboard(eventId: string, user: User) {
    await this.getOwnedEvent(eventId, user);

    const projectList = await this.dbR.query.projects.findMany({
      where: eq(projects.event_id, eventId),
      with: { votes: true, owner: true, collaborators: { with: { user: true } } },
    });

    const mapped = projectList.map((p) => ({
      id: p.id,
      name: p.name,
      repo: p.repo,
      image_url: p.image_url,
      demo: p.demo,
      description: p.description,
      points: p.votes.length,
      owner_id: p.owner_id,
      owner_name: p.owner.display_name || `${p.owner.first_name} ${p.owner.last_name}`.trim(),
      owner_email: p.owner.email,
      join_code: p.join_code,
      hours_spent: p.hours_spent,
      event_id: p.event_id,
      collaborators: p.collaborators.map((c) => ({
        user_id: c.user_id,
        display_name: c.user.display_name || `${c.user.first_name} ${c.user.last_name}`.trim(),
        email: c.user.email,
      })),
    }));

    mapped.sort((a, b) => b.points - a.points);
    return mapped;
  }

  async getEventVotes(eventId: string, user: User) {
    await this.getOwnedEvent(eventId, user);

    const voteList = await this.dbRo.query.votes.findMany({
      where: eq(votes.event_id, eventId),
    });
    return voteList.map((v) => ({
      id: v.id,
      voter_id: v.voter_id,
      project_id: v.project_id,
      event_id: v.event_id,
    }));
  }

  async getEventReferrals(eventId: string, user: User) {
    await this.getOwnedEvent(eventId, user);

    const referralList = await this.dbRo.query.referrals.findMany({
      where: eq(referrals.event_id, eventId),
    });
    return referralList.map((r) => ({
      id: r.id,
      content: r.content,
      user_id: r.user_id,
      event_id: r.event_id,
    }));
  }

  // ── Platform Settings ───────────────────────────────────────────────

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
}
