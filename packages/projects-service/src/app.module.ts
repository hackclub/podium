import { Module } from '@nestjs/common';
import { APP_GUARD } from '@nestjs/core';
import { ConfigModule, ConfigService } from '@nestjs/config';
import { JwtModule } from '@nestjs/jwt';
import { PassportModule } from '@nestjs/passport';
import { DrizzleModule, RedisModule, JwtStrategy, RateLimitGuard } from '@podium/shared';
import { HealthModule } from './health/health.module';
import { ProjectsModule } from './projects/projects.module';

@Module({
  imports: [
    ConfigModule.forRoot({
      isGlobal: true,
      envFilePath: '../../.env'
    }),
    DrizzleModule.forRootAsync(),
    RedisModule.forRootAsync(),
    PassportModule,
    JwtModule.registerAsync({
      inject: [ConfigService],
      useFactory: (config: ConfigService) => ({
        secret: config.get<string>('PODIUM_JWT_SECRET'),
        signOptions: {
          algorithm: config.get('PODIUM_JWT_ALGORITHM', 'HS256') as any,
        },
      }),
    }),
    HealthModule,
    ProjectsModule,
  ],
  providers: [
    JwtStrategy,
    { provide: APP_GUARD, useClass: RateLimitGuard },
  ],
})
export class AppModule {}
