import { Module } from '@nestjs/common';
import { ProjectsController } from './projects.controller';
import { ProjectsService } from './projects.service';
import { UploadService } from './upload.service';

@Module({
  controllers: [ProjectsController],
  providers: [ProjectsService, UploadService],
  exports: [ProjectsService],
})
export class ProjectsModule {}
