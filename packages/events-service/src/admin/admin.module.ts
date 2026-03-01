import { Module } from '@nestjs/common';
import { PlatformSettingsService } from '@podium/shared';
import { AdminController } from './admin.controller';
import { AdminService } from './admin.service';

@Module({
  controllers: [AdminController],
  providers: [AdminService, PlatformSettingsService],
})
export class AdminModule {}
