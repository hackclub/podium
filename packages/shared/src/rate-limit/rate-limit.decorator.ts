import { SetMetadata } from '@nestjs/common';

export const RATE_LIMIT_KEY = 'RATE_LIMIT';

export interface RateLimitOptions {
  limit: number;
  windowSeconds: number;
}

/** Apply a per-endpoint rate limit (overrides the global default). */
export const RateLimit = (limit: number, windowSeconds: number) =>
  SetMetadata(RATE_LIMIT_KEY, { limit, windowSeconds } as RateLimitOptions);

/** Exempt this endpoint from rate limiting (e.g. health checks). */
export const SkipRateLimit = () => SetMetadata(RATE_LIMIT_KEY, null);
