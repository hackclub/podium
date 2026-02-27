import {
  CanActivate,
  ExecutionContext,
  ForbiddenException,
  Inject,
  Injectable,
} from '@nestjs/common';
import { eq, and, or } from 'drizzle-orm';
import { DRIZZLE } from '../db/drizzle.module';
import { type Database } from '../db/client';
import { events, eventAttendees, getFeatureFlagsList } from '../db/schema';

@Injectable()
export class AdminGuard implements CanActivate {
  constructor(@Inject(DRIZZLE) private readonly db: Database) {}

  async canActivate(context: ExecutionContext): Promise<boolean> {
    const request = context.switchToHttp().getRequest();
    const user = request.user;

    if (!user) {
      throw new ForbiddenException('Not authenticated');
    }

    // Superadmins can access everything
    if (user.is_superadmin) {
      return true;
    }

    // Check if user owns or is POC/RM of the specific event
    const eventId = request.params?.event_id;
    if (eventId) {
      const event = await this.db.query.events.findFirst({
        where: eq(events.id, eventId),
      });

      // Flagship events are superadmin-only
      if (event && getFeatureFlagsList(event).includes('flagship')) {
        throw new ForbiddenException('Superadmin access required for flagship events');
      }

      if (
        event &&
        (event.owner_id === user.id ||
          event.poc_id === user.id ||
          event.rm_id === user.id)
      ) {
        return true;
      }
      // Allow is_admin users who are attendees of this event
      if (user.is_admin) {
        const attendee = await this.db.query.eventAttendees.findFirst({
          where: and(
            eq(eventAttendees.event_id, eventId),
            eq(eventAttendees.user_id, user.id),
          ),
        });
        if (attendee) {
          return true;
        }
      }
      throw new ForbiddenException('Admin access required');
    }

    // For list/create endpoints (no event_id), allow if user is admin, owns, or is POC/RM of any event
    if (user.is_admin) {
      return true;
    }
    const ownedOrPocEvent = await this.db.query.events.findFirst({
      where: or(
        eq(events.owner_id, user.id),
        eq(events.poc_id, user.id),
        eq(events.rm_id, user.id),
      ),
    });
    if (ownedOrPocEvent) {
      return true;
    }

    throw new ForbiddenException('Admin access required');
  }
}
