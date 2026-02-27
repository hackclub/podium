import { Inject, Injectable, Logger } from '@nestjs/common';
import type Redis from 'ioredis';
import axios from 'axios';
import * as cheerio from 'cheerio';
import { REDIS } from '@podium/shared';

const ITCH_URL_PATTERN =
  /^(https?:\/\/)?[a-zA-Z0-9\-_]+\.itch\.io\/[a-zA-Z0-9\-_]+/i;

const RATE_LIMIT_KEY = 'itch:last_request';
const MIN_INTERVAL_MS = 1000;

export function isItchUrl(url: string): boolean {
  return ITCH_URL_PATTERN.test(url);
}

/**
 * Lua script that enforces a global minimum interval between itch.io requests.
 *
 * KEYS[1] = rate limit key
 * ARGV[1] = current time (ms)
 * ARGV[2] = minimum interval (ms)
 *
 * Returns the number of ms the caller must wait (0 = proceed immediately).
 */
const ACQUIRE_SLOT_LUA = `
local key = KEYS[1]
local now = tonumber(ARGV[1])
local interval = tonumber(ARGV[2])

local last = redis.call('GET', key)
if last then
  last = tonumber(last)
  local next_allowed = last + interval
  if now < next_allowed then
    return next_allowed - now
  end
end

redis.call('SET', key, now, 'PX', interval * 2)
return 0
`;

@Injectable()
export class ItchValidatorService {
  private readonly logger = new Logger(ItchValidatorService.name);

  constructor(@Inject(REDIS) private readonly redis: Redis) {}

  /**
   * Check if an itch.io game is browser-playable.
   * Uses Redis to coordinate across replicas so we never exceed 1 req/sec to itch.io.
   */
  async isPlayable(url: string, timeout = 10000): Promise<boolean | null> {
    await this.acquireSlot();
    return this.fetchPlayable(url, timeout);
  }

  /**
   * Wait until we're allowed to make the next request to itch.io.
   * Retries up to 10 times (max ~10s wait) before giving up.
   */
  private async acquireSlot(): Promise<void> {
    for (let attempt = 0; attempt < 10; attempt++) {
      const waitMs = (await this.redis.eval(
        ACQUIRE_SLOT_LUA,
        1,
        RATE_LIMIT_KEY,
        Date.now().toString(),
        MIN_INTERVAL_MS.toString(),
      )) as number;

      if (waitMs <= 0) return;

      this.logger.debug(`Itch rate limit: waiting ${waitMs}ms (attempt ${attempt + 1})`);
      await new Promise((r) => setTimeout(r, waitMs));
    }
    // After 10 retries (~10s), proceed anyway rather than blocking the user forever
    this.logger.warn('Itch rate limit: exhausted retries, proceeding');
  }

  private async fetchPlayable(url: string, timeout: number): Promise<boolean | null> {
    try {
      const response = await axios.get(url, {
        timeout,
        maxRedirects: 5,
      });
      const $ = cheerio.load(response.data);
      return $('.game_frame').length > 0;
    } catch (err) {
      if (axios.isAxiosError(err) && err.response?.status === 429) {
        this.logger.warn('Itch.io returned 429 Too Many Requests, skipping check');
        return null;
      }
      return false;
    }
  }
}
