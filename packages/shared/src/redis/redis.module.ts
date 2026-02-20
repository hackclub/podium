import { Module, Global, DynamicModule } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import Redis from 'ioredis';

export const REDIS = Symbol('REDIS');

@Global()
@Module({})
export class RedisModule {
  static forRootAsync(): DynamicModule {
    return {
      module: RedisModule,
      providers: [
        {
          provide: REDIS,
          inject: [ConfigService],
          useFactory: (config: ConfigService) => {
            const sentinels = config.get<string>('REDIS_SENTINELS', '');
            const sentinelName = config.get<string>(
              'REDIS_SENTINEL_NAME',
              'mymaster',
            );

            const password = config.get<string>('REDIS_PASSWORD', '');

            if (sentinels) {
              const sentinelList = sentinels.split(',').map((s) => {
                const [host, port] = s.trim().split(':');
                return { host, port: parseInt(port, 10) };
              });
              return new Redis({
                sentinels: sentinelList,
                name: sentinelName,
                password: password || undefined,
                sentinelPassword: password || undefined,
                lazyConnect: false,
                enableReadyCheck: true,
                maxRetriesPerRequest: 3,
                retryStrategy: (times: number) =>
                  Math.min(times * 200, 2000),
              });
            }

            const url = config.get<string>(
              'REDIS_URL',
              'redis://localhost:6379',
            );
            return new Redis(url, {
              password: password || undefined,
              lazyConnect: false,
              enableReadyCheck: true,
              maxRetriesPerRequest: 3,
            });
          },
        },
      ],
      exports: [REDIS],
    };
  }
}
