import { Module } from '@nestjs/common';
import { PlatformSettingsService } from '@podium/shared';
import { ProjectsController } from './projects.controller';
import { ProjectsService } from './projects.service';
import { UploadService } from './upload.service';
import { ItchValidatorService } from './validators/itch-validator';
import { GitHubValidatorService } from './validators/github-validator';

@Module({
  controllers: [ProjectsController],
  providers: [ProjectsService, UploadService, ItchValidatorService, GitHubValidatorService, PlatformSettingsService],
  exports: [ProjectsService],
})
export class ProjectsModule {}
