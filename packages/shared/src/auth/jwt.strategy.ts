import { Inject, Injectable, UnauthorizedException } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { PassportStrategy } from '@nestjs/passport';
import { Strategy, ExtractJwt, type StrategyOptionsWithoutRequest } from 'passport-jwt';
import { eq } from 'drizzle-orm';
import type Redis from 'ioredis';
import { DRIZZLE } from '../db/drizzle.module';
import { type Database } from '../db/client';
import { users } from '../db/schema';
import { REDIS } from '../redis/redis.module';

/** Cache TTL for JWT user lookups (seconds). */
const USER_CACHE_TTL = 30;
const USER_CACHE_PREFIX = 'jwt_user:';

@Injectable()
export class JwtStrategy extends PassportStrategy(Strategy) {
  constructor(
    config: ConfigService,
    @Inject(DRIZZLE) private readonly db: Database,
    @Inject(REDIS) private readonly redis: Redis,
  ) {
    super({
      jwtFromRequest: ExtractJwt.fromAuthHeaderAsBearerToken(),
      secretOrKey: config.get<string>('PODIUM_JWT_SECRET')!,
      algorithms: [config.get<string>('PODIUM_JWT_ALGORITHM', 'HS256')!],
    } as StrategyOptionsWithoutRequest);
  }

  async validate(payload: {
    sub: string;
    token_type: string;
  }) {
    if (payload.token_type !== 'access') {
      throw new UnauthorizedException();
    }

    const cacheKey = `${USER_CACHE_PREFIX}${payload.sub}`;

    // Try Redis cache first
    try {
      const cached = await this.redis.get(cacheKey);
      if (cached) {
        return JSON.parse(cached);
      }
    } catch {
      // Redis down — fall through to DB
    }

    const user = await this.db.query.users.findFirst({
      where: eq(users.email, payload.sub),
      columns: {
        id: true,
        email: true,
        display_name: true,
        first_name: true,
        last_name: true,
        is_admin: true,
        is_superadmin: true,
      },
    });
    if (!user) {
      throw new UnauthorizedException();
    }

    // Cache for subsequent requests
    try {
      await this.redis.set(cacheKey, JSON.stringify(user), 'EX', USER_CACHE_TTL);
    } catch {
      // Non-fatal — next request will just hit DB again
    }

    return user;
  }
}
