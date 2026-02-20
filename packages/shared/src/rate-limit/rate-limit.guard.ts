import {
  CanActivate,
  ExecutionContext,
  HttpException,
  HttpStatus,
  Inject,
  Injectable,
  Logger,
} from '@nestjs/common';
import { Reflector } from '@nestjs/core';
import type Redis from 'ioredis';
import { REDIS } from '../redis/redis.module';
import { RATE_LIMIT_KEY, type RateLimitOptions } from './rate-limit.decorator';

// Very permissive defaults — at hackathon venues hundreds of users may
// share the same public IP. Authenticated endpoints key on the JWT email
// so limits are per-user regardless, but unauthenticated endpoints fall
// back to IP keying and must tolerate the full venue behind one IP.
const DEFAULT_LIMIT = 600;
const DEFAULT_WINDOW = 60;

/**
 * Sliding-window rate limiter using Redis sorted sets.
 *
 * Atomically: remove expired entries, count remaining,
 * add new entry if under limit, set key TTL.
 *
 * Returns [allowed (0|1), count, resetAtMs].
 */
const SLIDING_WINDOW_LUA = `
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
local member = ARGV[4]

local min = now - window
redis.call('ZREMRANGEBYSCORE', key, '-inf', min)

local count = redis.call('ZCARD', key)
if count < limit then
  redis.call('ZADD', key, now, member)
  redis.call('PEXPIRE', key, window)
  return {1, count + 1, now + window}
else
  local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
  local resetAt = 0
  if #oldest >= 2 then
    resetAt = tonumber(oldest[2]) + window
  end
  return {0, count, resetAt}
end
`;

@Injectable()
export class RateLimitGuard implements CanActivate {
  private readonly logger = new Logger(RateLimitGuard.name);

  constructor(
    @Inject(REDIS) private readonly redis: Redis,
    private readonly reflector: Reflector,
  ) {}

  async canActivate(context: ExecutionContext): Promise<boolean> {
    const meta = this.reflector.getAllAndOverride<RateLimitOptions | null>(
      RATE_LIMIT_KEY,
      [context.getHandler(), context.getClass()],
    );

    // @SkipRateLimit() sets metadata to null
    if (meta === null) return true;

    const limit = meta?.limit ?? DEFAULT_LIMIT;
    const windowSeconds = meta?.windowSeconds ?? DEFAULT_WINDOW;
    const windowMs = windowSeconds * 1000;

    const request = context.switchToHttp().getRequest();
    const identifier = this.getIdentifier(request);
    const route = `${request.method}:${context.getClass().name}:${context.getHandler().name}`;
    const key = `rl:${route}:${identifier}`;

    const now = Date.now();
    const member = `${now}:${Math.random().toString(36).slice(2, 8)}`;

    try {
      const [allowed, count, resetAt] = (await this.redis.eval(
        SLIDING_WINDOW_LUA,
        1,
        key,
        now.toString(),
        windowMs.toString(),
        limit.toString(),
        member,
      )) as [number, number, number];

      const response = context.switchToHttp().getResponse();
      response.setHeader('X-RateLimit-Limit', limit);
      response.setHeader('X-RateLimit-Remaining', Math.max(0, limit - count));
      response.setHeader(
        'X-RateLimit-Reset',
        Math.ceil(resetAt / 1000).toString(),
      );

      if (!allowed) {
        const retryAfter = Math.ceil((resetAt - now) / 1000);
        response.setHeader('Retry-After', retryAfter.toString());
        throw new HttpException(
          {
            statusCode: HttpStatus.TOO_MANY_REQUESTS,
            message: 'Too many requests',
            retryAfter,
          },
          HttpStatus.TOO_MANY_REQUESTS,
        );
      }

      return true;
    } catch (err) {
      if (err instanceof HttpException) throw err;
      // Redis down → fail open
      this.logger.error(`Rate limit check failed, allowing request: ${err}`);
      return true;
    }
  }

  /**
   * Extract identity from JWT (without verification) or fall back to IP.
   * Same approach as SentryUserInterceptor.
   */
  private getIdentifier(request: any): string {
    const auth = request.headers?.authorization ?? '';
    if (auth.startsWith('Bearer ')) {
      try {
        const payload = JSON.parse(
          Buffer.from(auth.split('.')[1], 'base64').toString(),
        );
        if (payload?.sub) return `user:${payload.sub}`;
      } catch {
        // malformed token — fall through to IP
      }
    }
    return `ip:${this.getClientIp(request)}`;
  }

  private getClientIp(request: any): string {
    const forwarded = request.headers?.['x-forwarded-for'];
    if (forwarded) {
      return (typeof forwarded === 'string' ? forwarded : forwarded[0])
        .split(',')[0]
        .trim();
    }
    return request.ip ?? request.socket?.remoteAddress ?? 'unknown';
  }
}
