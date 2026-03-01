import {
  Controller,
  Get,
  Post,
  Put,
  Delete,
  Body,
  Param,
  Query,
  UseGuards,
  UseInterceptors,
  UploadedFile,
  BadRequestException,
  ParseUUIDPipe,
} from '@nestjs/common';
import { FileInterceptor } from '@nestjs/platform-express';
import { memoryStorage } from 'multer';
import { User, JwtAuthGuard, OptionalJwtAuthGuard, AdminGuard, CurrentUser, RateLimit } from '@podium/shared';
import { ProjectsService } from './projects.service';
import { UploadService } from './upload.service';
import {
  IsString,
  IsOptional,
  IsNotEmpty,
  IsNumber,
  IsUUID,
  IsEmail,
  IsDateString,
  IsArray,
  ValidateNested,
  Min,
  Matches,
} from 'class-validator';
import { Type } from 'class-transformer';

class TeammateDto {
  @IsEmail()
  email!: string;

  @IsOptional()
  @IsString()
  first_name?: string;

  @IsOptional()
  @IsString()
  last_name?: string;

  @IsOptional()
  @IsString()
  phone?: string;

  @IsOptional()
  @IsString()
  street_1?: string;

  @IsOptional()
  @IsString()
  street_2?: string;

  @IsOptional()
  @IsString()
  city?: string;

  @IsOptional()
  @IsString()
  state?: string;

  @IsOptional()
  @IsString()
  zip_code?: string;

  @IsOptional()
  @IsString()
  country?: string;

  @IsOptional()
  @IsDateString()
  dob?: string;
}

class CreateProjectDto {
  @IsString()
  @IsNotEmpty()
  name!: string;

  @IsString()
  @IsNotEmpty()
  @Matches(/^https?:\/\/github\.com\/[a-zA-Z0-9\-_.]+\/[a-zA-Z0-9\-_.]+\/?$/, {
    message: 'repo must be a valid GitHub repository URL (e.g. https://github.com/user/repo)',
  })
  repo!: string;

  @IsString()
  @IsNotEmpty()
  image_url!: string;

  @IsString()
  @IsNotEmpty()
  demo!: string;

  @IsString()
  @IsNotEmpty()
  description!: string;

  @IsNumber()
  @Min(1)
  hours_spent!: number;

  @IsUUID('4')
  event_id!: string;

  @IsOptional()
  @IsArray()
  @ValidateNested({ each: true })
  @Type(() => TeammateDto)
  teammates?: TeammateDto[];
}

class AdminAddCollaboratorDto {
  @IsEmail()
  email!: string;

  @IsOptional()
  @IsString()
  first_name?: string;

  @IsOptional()
  @IsString()
  last_name?: string;

  @IsOptional()
  @IsString()
  phone?: string;

  @IsOptional()
  @IsString()
  street_1?: string;

  @IsOptional()
  @IsString()
  street_2?: string;

  @IsOptional()
  @IsString()
  city?: string;

  @IsOptional()
  @IsString()
  state?: string;

  @IsOptional()
  @IsString()
  zip_code?: string;

  @IsOptional()
  @IsString()
  country?: string;

  @IsOptional()
  @IsDateString()
  dob?: string;
}

class OwnerAddCollaboratorDto {
  @IsEmail()
  email!: string;

  @IsOptional()
  @IsString()
  first_name?: string;

  @IsOptional()
  @IsString()
  last_name?: string;

  @IsOptional()
  @IsString()
  phone?: string;

  @IsOptional()
  @IsString()
  street_1?: string;

  @IsOptional()
  @IsString()
  street_2?: string;

  @IsOptional()
  @IsString()
  city?: string;

  @IsOptional()
  @IsString()
  state?: string;

  @IsOptional()
  @IsString()
  zip_code?: string;

  @IsOptional()
  @IsString()
  country?: string;

  @IsOptional()
  @IsDateString()
  dob?: string;
}

class UpdateProjectDto {
  @IsOptional()
  @IsString()
  name?: string;

  @IsOptional()
  @IsString()
  repo?: string;

  @IsOptional()
  @IsString()
  image_url?: string;

  @IsOptional()
  @IsString()
  demo?: string;

  @IsOptional()
  @IsString()
  description?: string;

  @IsOptional()
  @IsNumber()
  hours_spent?: number;
}

@Controller('projects')
export class ProjectsController {
  constructor(
    private readonly projectsService: ProjectsService,
    private readonly uploadService: UploadService,
  ) {}

  @Post('upload-screenshot')
  @UseGuards(JwtAuthGuard)
  @RateLimit(30, 60)
  @UseInterceptors(
    FileInterceptor('file', { storage: memoryStorage(), limits: { fileSize: 5 * 1024 * 1024 } }),
  )
  async uploadScreenshot(
    @UploadedFile() file: Express.Multer.File,
    @Query('event_slug') eventSlug: string,
  ) {
    if (!file) throw new BadRequestException('No file provided');
    if (!eventSlug) throw new BadRequestException('event_slug query param is required');
    const url = await this.uploadService.uploadScreenshot(file, eventSlug);
    return { url };
  }

  @Get('mine')
  @UseGuards(JwtAuthGuard)
  async getMyProjects(@CurrentUser() user: User) {
    return this.projectsService.getMyProjects(user);
  }

  @Post()
  @UseGuards(JwtAuthGuard)
  @RateLimit(20, 60)
  async createProject(
    @Body() body: CreateProjectDto,
    @CurrentUser() user: User,
  ) {
    return this.projectsService.createProject(body, user);
  }

  @Post('join')
  @UseGuards(JwtAuthGuard)
  @RateLimit(20, 60)
  async joinProject(
    @Query('join_code') joinCode: string,
    @CurrentUser() user: User,
  ) {
    return this.projectsService.joinProject(joinCode, user);
  }

  @Post('validate')
  @UseGuards(JwtAuthGuard)
  @RateLimit(30, 60)
  async validateProject(@Query('project_id') projectId: string) {
    return this.projectsService.validateProject(projectId);
  }

  @Post(':project_id/collaborators')
  @UseGuards(JwtAuthGuard)
  @RateLimit(30, 60)
  async ownerAddCollaborator(
    @Param('project_id', ParseUUIDPipe) projectId: string,
    @Body() body: OwnerAddCollaboratorDto,
    @CurrentUser() user: User,
  ) {
    return this.projectsService.ownerAddCollaborator(projectId, body, user);
  }

  @Delete(':project_id/collaborators/:user_id')
  @UseGuards(JwtAuthGuard)
  async ownerRemoveCollaborator(
    @Param('project_id', ParseUUIDPipe) projectId: string,
    @Param('user_id', ParseUUIDPipe) userId: string,
    @CurrentUser() user: User,
  ) {
    return this.projectsService.ownerRemoveCollaborator(projectId, userId, user);
  }

  @Put(':project_id')
  @UseGuards(JwtAuthGuard)
  async updateProject(
    @Param('project_id', ParseUUIDPipe) projectId: string,
    @Body() body: UpdateProjectDto,
    @CurrentUser() user: User,
  ) {
    return this.projectsService.updateProject(projectId, body, user);
  }

  @Delete(':project_id')
  @UseGuards(JwtAuthGuard)
  async deleteProject(
    @Param('project_id', ParseUUIDPipe) projectId: string,
    @CurrentUser() user: User,
  ) {
    return this.projectsService.deleteProject(projectId, user);
  }

  @Get(':project_id')
  @UseGuards(OptionalJwtAuthGuard)
  async getProject(@Param('project_id', ParseUUIDPipe) projectId: string, @CurrentUser() user?: User) {
    return this.projectsService.getProject(projectId, user);
  }

  // ── Admin endpoints ──────────────────────────────────────────────

  @Put('admin/:project_id')
  @UseGuards(JwtAuthGuard, AdminGuard)
  async adminUpdateProject(
    @Param('project_id', ParseUUIDPipe) projectId: string,
    @Body() body: UpdateProjectDto,
    @CurrentUser() user: User,
  ) {
    return this.projectsService.adminUpdateProject(projectId, body, user);
  }

  @Delete('admin/:project_id')
  @UseGuards(JwtAuthGuard, AdminGuard)
  async adminDeleteProject(
    @Param('project_id', ParseUUIDPipe) projectId: string,
    @CurrentUser() user: User,
  ) {
    return this.projectsService.adminDeleteProject(projectId, user);
  }

  @Post('admin/:project_id/collaborators')
  @UseGuards(JwtAuthGuard, AdminGuard)
  async adminAddCollaborator(
    @Param('project_id', ParseUUIDPipe) projectId: string,
    @Body() body: AdminAddCollaboratorDto,
    @CurrentUser() user: User,
  ) {
    return this.projectsService.adminAddCollaborator(projectId, body, user);
  }

  @Delete('admin/:project_id/collaborators/:user_id')
  @UseGuards(JwtAuthGuard, AdminGuard)
  async adminRemoveCollaborator(
    @Param('project_id', ParseUUIDPipe) projectId: string,
    @Param('user_id', ParseUUIDPipe) userId: string,
    @CurrentUser() user: User,
  ) {
    return this.projectsService.adminRemoveCollaborator(projectId, userId, user);
  }
}
