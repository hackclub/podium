import { Controller, Inject, Logger } from '@nestjs/common';
import { EventPattern, Payload } from '@nestjs/microservices';
import { eq, and, inArray } from 'drizzle-orm';
import {
  DRIZZLE_RW,
  type Database,
  events,
  projects,
  votes,
  users,
  eventAttendees,
  projectCollaborators,
  getMaxVotesPerUser,
} from '@podium/shared';

interface VoteMessage {
  userId: string;
  eventId: string;
  projectIds: string[];
}

@Controller()
export class VoteConsumer {
  private readonly logger = new Logger(VoteConsumer.name);

  constructor(@Inject(DRIZZLE_RW) private readonly db: Database) {}

  @EventPattern('votes')
  async handleVote(@Payload() message: VoteMessage) {
    try {
      await this.processVote(message);
    } catch (err) {
      this.logger.error(
        `Failed to process vote: ${err instanceof Error ? err.message : err}`,
        err instanceof Error ? err.stack : undefined,
      );
    }
  }

  private async processVote(message: VoteMessage) {
    const { userId, eventId, projectIds } = message;

    // Deduplicate
    const uniqueProjectIds = [...new Set(projectIds)];
    if (uniqueProjectIds.length === 0) return;

    // Batch all prerequisite lookups in parallel — same checks as before,
    // just fetched in one round-trip instead of N sequential queries.
    const [user, event, attendeeRow, existingVotes, candidateProjects, collabRows] =
      await Promise.all([
        this.db.query.users.findFirst({
          where: eq(users.id, userId),
          columns: { id: true },
        }),
        this.db.query.events.findFirst({
          where: eq(events.id, eventId),
          with: { projects: { columns: { id: true } } },
        }),
        this.db.query.eventAttendees.findFirst({
          where: and(
            eq(eventAttendees.event_id, eventId),
            eq(eventAttendees.user_id, userId),
          ),
          columns: { id: true },
        }),
        this.db.query.votes.findMany({
          where: and(eq(votes.event_id, eventId), eq(votes.voter_id, userId)),
          columns: { project_id: true },
        }),
        this.db.query.projects.findMany({
          where: inArray(projects.id, uniqueProjectIds),
          columns: { id: true, event_id: true, owner_id: true },
        }),
        this.db.query.projectCollaborators.findMany({
          where: and(
            inArray(projectCollaborators.project_id, uniqueProjectIds),
            eq(projectCollaborators.user_id, userId),
          ),
          columns: { project_id: true },
        }),
      ]);

    if (!user) {
      this.logger.warn(`Vote rejected: user ${userId} not found`);
      return;
    }

    if (!event) {
      this.logger.warn(`Vote rejected: event ${eventId} not found`);
      return;
    }
    if (!event.votable) {
      this.logger.warn(`Vote rejected: voting not enabled for event ${eventId}`);
      return;
    }

    if (!attendeeRow) {
      this.logger.warn(`Vote rejected: user ${userId} not attending event ${eventId}`);
      return;
    }

    // Build lookup sets for O(1) checks
    const alreadyVotedProjectIds = new Set(existingVotes.map((v) => v.project_id));
    const projectMap = new Map(candidateProjects.map((p) => [p.id, p]));
    const collabProjectIds = new Set(collabRows.map((c) => c.project_id));

    const maxVotes = getMaxVotesPerUser();

    // Filter valid votes in memory — every security check is preserved
    const toInsert: { voter_id: string; project_id: string; event_id: string }[] = [];

    for (const projectId of uniqueProjectIds) {
      const project = projectMap.get(projectId);
      if (!project) {
        this.logger.warn(`Vote skipped: project ${projectId} not found`);
        continue;
      }
      if (project.event_id !== eventId) {
        this.logger.warn(`Vote skipped: project ${projectId} not in event ${eventId}`);
        continue;
      }
      if (alreadyVotedProjectIds.has(projectId)) {
        this.logger.warn(`Vote skipped: user ${userId} already voted for project ${projectId}`);
        continue;
      }
      if (userId === project.owner_id) {
        this.logger.warn(`Vote skipped: user ${userId} is owner of project ${projectId}`);
        continue;
      }
      if (collabProjectIds.has(projectId)) {
        this.logger.warn(`Vote skipped: user ${userId} is collaborator of project ${projectId}`);
        continue;
      }

      if (alreadyVotedProjectIds.size + toInsert.length >= maxVotes) {
        this.logger.warn(
          `Vote rejected: user ${userId} would exceed max votes (${maxVotes}) for event ${eventId}`,
        );
        break;
      }

      toInsert.push({
        voter_id: userId,
        project_id: projectId,
        event_id: eventId,
      });
    }

    // Batch insert all valid votes. onConflictDoNothing lets the DB
    // UNIQUE(voter_id, project_id) constraint handle any race conditions —
    // the constraint is the authoritative dedup guard.
    if (toInsert.length > 0) {
      await this.db.insert(votes).values(toInsert).onConflictDoNothing();
    }

    this.logger.log(`Processed ${toInsert.length} vote(s) from user ${userId} for event ${eventId}`);
  }
}
