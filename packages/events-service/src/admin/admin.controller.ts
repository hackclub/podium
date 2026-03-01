import {
  Controller,
  Get,
  Put,
  Post,
  Body,
  Param,
  UseGuards,
} from '@nestjs/common';
import { IsOptional, IsBoolean } from 'class-validator';
import { User, JwtAuthGuard, SuperAdminGuard, CurrentUser } from '@podium/shared';
import { AdminService } from './admin.service';

class UpdatePlatformSettingsDto {
  @IsOptional()
  @IsBoolean()
  github_validation_enabled?: boolean;

  @IsOptional()
  @IsBoolean()
  itch_validation_enabled?: boolean;
}

@Controller('events/admin')
@UseGuards(JwtAuthGuard)
export class AdminController {
  constructor(private readonly adminService: AdminService) {}

  // ── Platform Settings (must be before :event_id) ──────────────────

  @Get('platform-settings')
  @UseGuards(SuperAdminGuard)
  async getPlatformSettings() {
    return this.adminService.getPlatformSettings();
  }

  @Put('platform-settings')
  @UseGuards(SuperAdminGuard)
  async updatePlatformSettings(@Body() body: UpdatePlatformSettingsDto) {
    return this.adminService.updatePlatformSettings(body);
  }

  // ── Event-specific endpoints ──────────────────────────────────────

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
