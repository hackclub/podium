import { Module } from '@nestjs/common';
import { APP_GUARD } from '@nestjs/core';
import { ConfigModule } from '@nestjs/config';
import { DrizzleModule, RedisModule, RateLimitGuard } from '@podium/shared';
import { AuthModule } from './auth/auth.module';
import { HealthModule } from './health/health.module';
import { UsersModule } from './users/users.module';

@Module({
  imports: [
    ConfigModule.forRoot({
      isGlobal: true,
      envFilePath: '../../.env'
    }),
    DrizzleModule.forRootAsync(),
    RedisModule.forRootAsync(),
    AuthModule,
    HealthModule,
    UsersModule,
  ],
  providers: [
    { provide: APP_GUARD, useClass: RateLimitGuard },
  ],
})
export class AppModule {}
