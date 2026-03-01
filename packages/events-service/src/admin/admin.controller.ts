import {
  Controller,
  Get,
  Put,
  Body,
  UseGuards,
} from '@nestjs/common';
import { IsOptional, IsBoolean } from 'class-validator';
import { JwtAuthGuard, SuperAdminGuard } from '@podium/shared';
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

}
