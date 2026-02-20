import { Controller, Get, Inject } from '@nestjs/common';
import {
  HealthCheck,
  HealthCheckService,
  HealthIndicatorResult,
  MicroserviceHealthIndicator,
} from '@nestjs/terminus';
import { Transport } from '@nestjs/microservices';
import { ConfigService } from '@nestjs/config';
import { DRIZZLE_RW, type Database, SkipRateLimit } from '@podium/shared';
import { sql } from 'drizzle-orm';

@Controller('health')
@SkipRateLimit()
export class HealthController {
  constructor(
    private health: HealthCheckService,
    private microservice: MicroserviceHealthIndicator,
    private config: ConfigService,
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
    return this.health.check([
      () => this.checkDb(),
      () =>
        this.microservice.pingCheck('kafka', {
          transport: Transport.KAFKA,
          options: {
            client: {
              brokers: [
                this.config.get<string>('KAFKA_BROKER', 'localhost:9092'),
              ],
            },
          },
        }),
    ]);
  }

  private async checkDb(): Promise<HealthIndicatorResult> {
    await this.db.execute(sql`SELECT 1`);
    return { database: { status: 'up' } };
  }
}
