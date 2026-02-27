import { Inject, Injectable, Logger } from '@nestjs/common';
import type Redis from 'ioredis';
import axios from 'axios';
import { REDIS } from '@podium/shared';

const GITHUB_REPO_PATTERN =
  /^https?:\/\/github\.com\/([a-zA-Z0-9\-_.]+)\/([a-zA-Z0-9\-_.]+)\/?$/;

const RATE_LIMIT_KEY = 'github:last_request';
const MIN_INTERVAL_MS = 1000;
const CACHE_TTL_SUCCESS_MS = 300_000; // 5 min
const CACHE_TTL_FAILURE_MS = 60_000;  // 1 min

export function parseGitHubRepo(url: string): { owner: string; repo: string } | null {
  const match = url.match(GITHUB_REPO_PATTERN);
  if (!match) return null;
  return { owner: match[1], repo: match[2].replace(/\.git$/, '') };
}

/**
 * Lua script that enforces a global minimum interval between GitHub requests.
 * Identical to the one used by ItchValidatorService.
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
export class GitHubValidatorService {
  private readonly logger = new Logger(GitHubValidatorService.name);

  constructor(@Inject(REDIS) private readonly redis: Redis) {}

  /**
   * Check if a GitHub repo is publicly accessible.
   * Results are cached in Redis and outgoing requests are rate-limited
   * to avoid hitting GitHub's unauthenticated rate limit (60/hour/IP).
   */
  async isRepoAccessible(url: string, timeout = 5000): Promise<boolean | null> {
    const parsed = parseGitHubRepo(url);
    if (!parsed) return false;

    const cacheKey = `github:repo:${parsed.owner}/${parsed.repo}`;
    const cached = await this.redis.get(cacheKey);
    if (cached !== null) return cached === '1';

    await this.acquireSlot();
    const accessible = await this.fetchRepo(parsed, timeout);

    // Don't cache rate-limited responses
    if (accessible !== null) {
      await this.redis.set(
        cacheKey,
        accessible ? '1' : '0',
        'PX',
        accessible ? CACHE_TTL_SUCCESS_MS : CACHE_TTL_FAILURE_MS,
      );
    }
    return accessible;
  }

  /**
   * Wait until we're allowed to make the next request to GitHub.
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

      this.logger.debug(`GitHub rate limit: waiting ${waitMs}ms (attempt ${attempt + 1})`);
      await new Promise((r) => setTimeout(r, waitMs));
    }
    this.logger.warn('GitHub rate limit: exhausted retries, proceeding');
  }

  private async fetchRepo(
    parsed: { owner: string; repo: string },
    timeout: number,
  ): Promise<boolean | null> {
    try {
      const response = await axios.head(
        `https://github.com/${parsed.owner}/${parsed.repo}`,
        { timeout, maxRedirects: 5, validateStatus: (s) => s < 400 },
      );
      return response.status >= 200 && response.status < 400;
    } catch (err) {
      if (axios.isAxiosError(err) && err.response?.status === 429) {
        this.logger.warn('GitHub returned 429 Too Many Requests, skipping check');
        return null;
      }
      return false;
    }
  }
}
