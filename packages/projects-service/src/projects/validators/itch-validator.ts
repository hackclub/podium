import { Inject, Injectable, Logger } from '@nestjs/common';
import type Redis from 'ioredis';
import axios from 'axios';
import * as cheerio from 'cheerio';
import { REDIS } from '@podium/shared';

const ITCH_URL_PATTERN =
  /^(https?:\/\/)?[a-zA-Z0-9\-_]+\.itch\.io\/[a-zA-Z0-9\-_]+/i;

const RATE_LIMIT_KEY = 'itch:last_request';
const MIN_INTERVAL_MS = 1000;

// Only "playable" is cached: someone who just turned on "Run game in browser"
// has to see it on their next check, so a failure is always re-fetched.
const PLAYABLE_CACHE_PREFIX = 'itch:playable:';
const PLAYABLE_CACHE_TTL_S = 10 * 60;

export function isItchUrl(url: string): boolean {
  return ITCH_URL_PATTERN.test(url.trim());
}

/** `user.itch.io/game/` → `https://user.itch.io/game`, so one game has one cache entry. */
function normalizeItchUrl(url: string): string {
  const trimmed = url.trim();
  const parsed = new URL(/^https?:\/\//i.test(trimmed) ? trimmed : `https://${trimmed}`);
  return `https://${parsed.host.toLowerCase()}${parsed.pathname.replace(/\/+$/, '')}`;
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
   * Check if an itch.io game is browser-playable: true, false, or null when
   * itch.io couldn't answer (rate limit, timeout, outage).
   * Uses Redis to coordinate across replicas so we never exceed 1 req/sec to itch.io.
   */
  async isPlayable(url: string, timeout = 10000): Promise<boolean | null> {
    const normalized = normalizeItchUrl(url);
    const cacheKey = PLAYABLE_CACHE_PREFIX + normalized;
    if (await this.redis.get(cacheKey)) return true;

    await this.acquireSlot();
    const playable = await this.fetchPlayable(normalized, timeout);
    if (playable) {
      await this.redis.set(cacheKey, '1', 'EX', PLAYABLE_CACHE_TTL_S);
    }
    return playable;
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
      // .game_frame wraps itch.io's in-browser player; #game_drop is its other embed.
      return $('.game_frame').length > 0 || $('#game_drop').length > 0;
    } catch (err) {
      // A missing page is a real answer; anything else means itch.io didn't answer.
      if (axios.isAxiosError(err) && err.response?.status === 404) {
        return false;
      }
      if (axios.isAxiosError(err) && err.response?.status === 429) {
        this.logger.warn('Itch.io returned 429 Too Many Requests, skipping check');
      } else {
        this.logger.warn(`Itch.io check failed for ${url}: ${err instanceof Error ? err.message : err}`);
      }
      return null;
    }
  }
}
