import { Module, Global, DynamicModule } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { createDb } from './client';

export const DRIZZLE = Symbol('DRIZZLE');
/** Read-write primary — all inserts, updates, deletes */
export const DRIZZLE_RW = Symbol('DRIZZLE_RW');
/** Read-only hot standby — general reads */
export const DRIZZLE_RO = Symbol('DRIZZLE_RO');
/** Any replica (may lag) — leaderboard, public listings */
export const DRIZZLE_R = Symbol('DRIZZLE_R');

@Global()
@Module({})
export class DrizzleModule {
  static forRootAsync(): DynamicModule {
    return {
      module: DrizzleModule,
      providers: [
        {
          provide: DRIZZLE_RW,
          inject: [ConfigService],
          useFactory: (config: ConfigService) => {
            const url = config.get<string>('PODIUM_DATABASE_URL_RW')!;
            return createDb(url);
          },
        },
        {
          provide: DRIZZLE_RO,
          inject: [ConfigService],
          useFactory: (config: ConfigService) => {
            const url = config.get<string>('PODIUM_DATABASE_URL_RO')!;
            return createDb(url);
          },
        },
        {
          provide: DRIZZLE_R,
          inject: [ConfigService],
          useFactory: (config: ConfigService) => {
            const url = config.get<string>('PODIUM_DATABASE_URL_R')!;
            return createDb(url);
          },
        },
        // Legacy alias — resolves to the RW primary so existing code keeps working
        // during migration. Remove once all services have been updated.
        {
          provide: DRIZZLE,
          inject: [ConfigService],
          useFactory: (config: ConfigService) => {
            const url = config.get<string>('PODIUM_DATABASE_URL_RW')!;
            return createDb(url);
          },
        },
      ],
      exports: [DRIZZLE, DRIZZLE_RW, DRIZZLE_RO, DRIZZLE_R],
    };
  }
}
