import { Inject, Injectable } from '@nestjs/common';
import type Redis from 'ioredis';
import { REDIS } from '../redis';

const KEY_GITHUB = 'platform:github_validation_enabled';
const KEY_ITCH = 'platform:itch_validation_enabled';

type SettingKey = 'github_validation_enabled' | 'itch_validation_enabled';

@Injectable()
export class PlatformSettingsService {
  constructor(@Inject(REDIS) private readonly redis: Redis) {}

  async isGitHubValidationEnabled(): Promise<boolean> {
    const val = await this.redis.get(KEY_GITHUB);
    return val !== '0';
  }

  async isItchValidationEnabled(): Promise<boolean> {
    const val = await this.redis.get(KEY_ITCH);
    return val !== '0';
  }

  async getAll(): Promise<{ github_validation_enabled: boolean; itch_validation_enabled: boolean }> {
    const [github, itch] = await this.redis.mget(KEY_GITHUB, KEY_ITCH);
    return {
      github_validation_enabled: github !== '0',
      itch_validation_enabled: itch !== '0',
    };
  }

  async set(key: SettingKey, value: boolean): Promise<void> {
    await this.redis.set(`platform:${key}`, value ? '1' : '0');
  }
}
