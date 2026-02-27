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
  Inject,
  HttpCode,
  Sse,
} from '@nestjs/common';
import { ClientKafka } from '@nestjs/microservices';
import { Observable } from 'rxjs';
import { User, JwtAuthGuard, AdminGuard, SuperAdminGuard, CurrentUser } from '@podium/shared';
import { EventsService } from './events.service';
import { IsArray, IsString, IsUUID, IsOptional, IsEmail, IsInt, IsBoolean, Min, ValidateIf } from 'class-validator';

class CreateVotesDto {
  @IsArray()
  @IsUUID('4', { each: true })
  projects!: string[];

  @IsUUID('4')
  event!: string;
}

class TestEventCreateDto {
  @IsString()
  name!: string;

  @IsOptional()
  @IsString()
  description?: string;
}

class AdminAddAttendeeDto {
  @IsEmail()
  email!: string;
}

class CampfireImportDto {
  @IsString()
  cockpit_event_id!: string;
}

class AdminSetPointsDto {
  @IsInt()
  @Min(0)
  points!: number;
}

class AdminCreateEventDto {
  @IsString()
  name!: string;

  @IsString()
  slug!: string;

  @IsOptional()
  @IsString()
  description?: string;

  @IsOptional()
  @IsString()
  feature_flags_csv?: string;

  @IsOptional()
  @IsString()
  theme_name?: string;

  @IsOptional()
  @IsString()
  theme_background?: string;

  @IsOptional()
  @IsString()
  theme_font?: string;

  @IsOptional()
  @IsString()
  theme_primary?: string;

  @IsOptional()
  @IsString()
  theme_selected?: string;

  @IsOptional()
  @ValidateIf((o) => o.poc_id !== null)
  @IsUUID('4')
  poc_id?: string | null;

  @IsOptional()
  @ValidateIf((o) => o.rm_id !== null)
  @IsUUID('4')
  rm_id?: string | null;
}

class UpdatePlatformSettingsDto {
  @IsOptional()
  @IsBoolean()
  github_validation_enabled?: boolean;

  @IsOptional()
  @IsBoolean()
  itch_validation_enabled?: boolean;
}

@Controller('events')
export class EventsController {
  constructor(
    private readonly eventsService: EventsService,
    @Inject('KAFKA_SERVICE')
    private readonly kafkaClient: ClientKafka,
  ) {}

  // ── Public endpoints ─────────────────────────────────────────────

  @Get('official')
  async listOfficialEvents() {
    return this.eventsService.listOfficialEvents();
  }

  @Get()
  @UseGuards(JwtAuthGuard)
  async getAttendingEvents(@CurrentUser() user: User) {
    return this.eventsService.getAttendingEvents(user);
  }

  @Post('vote')
  @UseGuards(JwtAuthGuard)
  @HttpCode(202)
  async vote(@Body() body: CreateVotesDto, @CurrentUser() user: User) {
    // All three operations are independent — run in parallel.
    // ensureAttendee auto-registers the user if they aren't already,
    // so people who arrive after voting starts can still vote.
    await Promise.all([
      this.eventsService.checkVotable(body.event),
      this.eventsService.ensureAttendee(body.event, user.id),
      this.eventsService.checkNotOwnProject(user.id, body.projects),
    ]);

    this.kafkaClient.emit('votes', {
      key: body.event,
      value: JSON.stringify({
        userId: user.id,
        eventId: body.event,
        projectIds: body.projects,
      }),
    });

    return { message: 'Vote request accepted' };
  }

  @Get('id/:slug')
  async getEventIdBySlug(@Param('slug') slug: string) {
    return this.eventsService.getEventIdBySlug(slug);
  }

  // ── Admin endpoints ──────────────────────────────────────────────

  @Get('admin')
  @UseGuards(JwtAuthGuard, AdminGuard)
  async adminListEvents(@CurrentUser() user: User) {
    return this.eventsService.adminListEvents(user);
  }

  @Post('admin/create')
  @UseGuards(JwtAuthGuard, SuperAdminGuard)
  async adminCreateEvent(
    @Body() body: AdminCreateEventDto,
    @CurrentUser() user: User,
  ) {
    return this.eventsService.adminCreateEvent(body, user);
  }

  // ── Campfire Dashboard (superadmin) ─────────────────────────────

  @Get('admin/campfire/dashboard')
  @UseGuards(JwtAuthGuard, SuperAdminGuard)
  async getCampfireDashboard() {
    return this.eventsService.getCampfireDashboard();
  }

  // ── Public Dashboard (no auth, numbers + event names only) ─────

  @Get('public/dashboard')
  async getPublicDashboard() {
    return this.eventsService.getPublicDashboard();
  }

  // ── Campfire (superadmin) endpoints ─────────────────────────────

  @Get('admin/campfire/events')
  @UseGuards(JwtAuthGuard, AdminGuard)
  async getCampfireEvents(@CurrentUser() user: User) {
    return this.eventsService.getCampfireEvents(user);
  }

  @Post('admin/campfire/import')
  @UseGuards(JwtAuthGuard, AdminGuard)
  async importCampfireEvent(
    @Body() body: CampfireImportDto,
    @CurrentUser() user: User,
  ) {
    return this.eventsService.importCampfireEvent(
      body.cockpit_event_id,
      user,
    );
  }

  @Post('admin/campfire/sync')
  @UseGuards(JwtAuthGuard, AdminGuard)
  async syncCampfireEvent(
    @Body() body: CampfireImportDto,
    @CurrentUser() user: User,
  ) {
    return this.eventsService.syncCampfireEvent(
      body.cockpit_event_id,
      user,
    );
  }

  @Post('admin/campfire/sync-all')
  @UseGuards(JwtAuthGuard, AdminGuard)
  async syncAllCampfireEvents(@CurrentUser() user: User) {
    return this.eventsService.syncAllCampfireEvents(user);
  }

  @Post('admin/campfire/import-all-active')
  @UseGuards(JwtAuthGuard, AdminGuard)
  async importAllActiveCampfireEvents(@CurrentUser() user: User) {
    return this.eventsService.importAllActiveCampfireEvents(user);
  }

  @Post('admin/campfire/sync-airtable')
  @UseGuards(JwtAuthGuard, AdminGuard)
  async syncProjectsToAirtable(@CurrentUser() user: User) {
    return this.eventsService.syncAllProjectsToAirtable(user);
  }

  @Post('admin/campfire/validate-itch')
  @UseGuards(JwtAuthGuard, AdminGuard)
  async validateItchGames(@CurrentUser() user: User) {
    return this.eventsService.validateItchGames(user);
  }

  // ── Platform Settings (superadmin) ──────────────────────────────

  @Get('admin/platform-settings')
  @UseGuards(JwtAuthGuard, SuperAdminGuard)
  async getPlatformSettings() {
    return this.eventsService.getPlatformSettings();
  }

  @Put('admin/platform-settings')
  @UseGuards(JwtAuthGuard, SuperAdminGuard)
  async updatePlatformSettings(@Body() body: UpdatePlatformSettingsDto) {
    return this.eventsService.updatePlatformSettings(body);
  }

  @Get('admin/:event_id')
  @UseGuards(JwtAuthGuard, AdminGuard)
  async adminGetEvent(@Param('event_id') eventId: string) {
    return this.eventsService.adminGetEvent(eventId);
  }

  @Put('admin/:event_id')
  @UseGuards(JwtAuthGuard, AdminGuard)
  async adminUpdateEvent(
    @Param('event_id') eventId: string,
    @Body() body: Record<string, any>,
  ) {
    return this.eventsService.adminUpdateEvent(eventId, body);
  }

  @Delete('admin/:event_id')
  @UseGuards(JwtAuthGuard, AdminGuard)
  async adminDeleteEvent(
    @Param('event_id') eventId: string,
    @CurrentUser() user: User,
  ) {
    return this.eventsService.adminDeleteEvent(eventId, user);
  }

  @Get('admin/:event_id/attendees')
  @UseGuards(JwtAuthGuard, AdminGuard)
  async adminGetAttendees(@Param('event_id') eventId: string) {
    return this.eventsService.adminGetAttendees(eventId);
  }

  @Post('admin/:event_id/attendees')
  @UseGuards(JwtAuthGuard, AdminGuard)
  async adminAddAttendee(
    @Param('event_id') eventId: string,
    @Body() body: AdminAddAttendeeDto,
  ) {
    return this.eventsService.adminAddAttendee(eventId, body.email);
  }

  @Delete('admin/:event_id/attendees/:user_id')
  @UseGuards(JwtAuthGuard, AdminGuard)
  async adminRemoveAttendee(
    @Param('event_id') eventId: string,
    @Param('user_id') userId: string,
  ) {
    return this.eventsService.adminRemoveAttendee(eventId, userId);
  }

  @Post('admin/:event_id/sync-cockpit')
  @UseGuards(JwtAuthGuard, AdminGuard)
  async adminSyncFromCockpit(@Param('event_id') eventId: string) {
    return this.eventsService.syncCampfireEventByPodiumId(eventId);
  }

  @Post('admin/:event_id/sync-airtable')
  @UseGuards(JwtAuthGuard, AdminGuard)
  async adminSyncEventToAirtable(
    @Param('event_id') eventId: string,
    @CurrentUser() user: User,
  ) {
    return this.eventsService.syncEventProjectsToAirtable(eventId, user);
  }

  @Get('admin/:event_id/stats')
  @UseGuards(JwtAuthGuard, AdminGuard)
  async adminGetEventStats(@Param('event_id') eventId: string) {
    return this.eventsService.adminGetEventStats(eventId);
  }

  @Get('admin/:event_id/leaderboard')
  @UseGuards(JwtAuthGuard, AdminGuard)
  async adminGetLeaderboard(@Param('event_id') eventId: string) {
    return this.eventsService.adminGetLeaderboard(eventId);
  }

  @Put('admin/:event_id/projects/:project_id/points')
  @UseGuards(JwtAuthGuard, AdminGuard)
  async adminSetProjectPoints(
    @Param('event_id') eventId: string,
    @Param('project_id') projectId: string,
    @Body() body: AdminSetPointsDto,
  ) {
    return this.eventsService.adminSetProjectPoints(eventId, projectId, body.points);
  }

  // ── Test endpoints ───────────────────────────────────────────────

  @Post('test/create')
  @UseGuards(JwtAuthGuard)
  async createTestEvent(
    @Body() body: TestEventCreateDto,
    @CurrentUser() user: User,
  ) {
    return this.eventsService.createTestEvent(
      body.name,
      body.description ?? '',
      user,
    );
  }

  @Post('test/cleanup')
  async cleanupTestData() {
    return this.eventsService.cleanupTestData();
  }

  // ── SSE endpoint ────────────────────────────────────────────────

  @Sse(':event_id/stage-stream')
  stageStream(@Param('event_id') eventId: string): Observable<{ data: any }> {
    return this.eventsService.subscribeToStageChanges(eventId);
  }

  // ── Parameterized public endpoints (must be last) ────────────────

  @Get(':event_id/voter-count')
  async getUniqueVoterCount(@Param('event_id') eventId: string) {
    return this.eventsService.getUniqueVoterCount(eventId);
  }

  @Get(':event_id/my-votes')
  @UseGuards(JwtAuthGuard)
  async getMyVotes(
    @Param('event_id') eventId: string,
    @CurrentUser() user: User,
  ) {
    return this.eventsService.getMyVotes(eventId, user.id);
  }

  @Get(':event_id/projects')
  async getEventProjects(
    @Param('event_id') eventId: string,
    @Query('leaderboard') leaderboard: string,
  ) {
    return this.eventsService.getEventProjects(
      eventId,
      leaderboard === 'true',
    );
  }

  @Post(':event_id/attend')
  @UseGuards(JwtAuthGuard)
  async attendEvent(
    @Param('event_id') eventId: string,
    @CurrentUser() user: User,
  ) {
    return this.eventsService.attendEvent(eventId, user);
  }

  @Get(':event_id')
  async getEvent(@Param('event_id') eventId: string) {
    return this.eventsService.getEventById(eventId);
  }
}
