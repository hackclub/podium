import { Controller, Get, Inject } from '@nestjs/common';
import {
  HealthCheck,
  HealthCheckService,
  HealthIndicatorResult,
} from '@nestjs/terminus';
import { DRIZZLE_RW, type Database, SkipRateLimit } from '@podium/shared';
import { sql } from 'drizzle-orm';

@Controller('health')
@SkipRateLimit()
export class HealthController {
  constructor(
    private health: HealthCheckService,
    @Inject(DRIZZLE_RW) private readonly db: Database,
  ) {}

  @Get('live')
  @HealthCheck()
  liveness() {
    return this.health.check([]);
  }

  @Get('ready')
  @HealthCheck()
  readiness() {
    return this.health.check([() => this.checkDb()]);
  }

  private async checkDb(): Promise<HealthIndicatorResult> {
    await this.db.execute(sql`SELECT 1`);
    return { database: { status: 'up' } };
  }
}
