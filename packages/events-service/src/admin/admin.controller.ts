import {
  Controller,
  Get,
  Post,
  Body,
  Param,
  UseGuards,
} from '@nestjs/common';
import { User, JwtAuthGuard, CurrentUser } from '@podium/shared';
import { AdminService } from './admin.service';

@Controller('events/admin')
@UseGuards(JwtAuthGuard)
export class AdminController {
  constructor(private readonly adminService: AdminService) {}

  @Get(':event_id')
  async getEventAdmin(
    @Param('event_id') eventId: string,
    @CurrentUser() user: User,
  ) {
    return this.adminService.getEventAdmin(eventId, user);
  }

  @Get(':event_id/attendees')
  async getEventAttendees(
    @Param('event_id') eventId: string,
    @CurrentUser() user: User,
  ) {
    return this.adminService.getEventAttendees(eventId, user);
  }

  @Post(':event_id/remove-attendee')
  async removeAttendee(
    @Param('event_id') eventId: string,
    @Body('user_id') userId: string,
    @CurrentUser() user: User,
  ) {
    return this.adminService.removeAttendee(eventId, userId, user);
  }

  @Get(':event_id/leaderboard')
  async getEventLeaderboard(
    @Param('event_id') eventId: string,
    @CurrentUser() user: User,
  ) {
    return this.adminService.getEventLeaderboard(eventId, user);
  }

  @Get(':event_id/votes')
  async getEventVotes(
    @Param('event_id') eventId: string,
    @CurrentUser() user: User,
  ) {
    return this.adminService.getEventVotes(eventId, user);
  }

  @Get(':event_id/referrals')
  async getEventReferrals(
    @Param('event_id') eventId: string,
    @CurrentUser() user: User,
  ) {
    return this.adminService.getEventReferrals(eventId, user);
  }
}
