import { Pool } from 'pg';
import { drizzle } from 'drizzle-orm/node-postgres';
import * as schema from './schema';

/**
 * Default pool size per connection endpoint. Each service creates up to
 * 4 pools (RW, RO, R, legacy DRIZZLE). With 2 replicas per service ×
 * 3 services, total max connections ≈ 4 × 20 × 6 = 480, which fits
 * comfortably within PostgreSQL's default max_connections (typically
 * 200–400 per endpoint in a HA cluster with pgBouncer, or higher with
 * CloudNativePG defaults).
 *
 * Tune via the PODIUM_DB_POOL_MAX env var if needed.
 */
const DEFAULT_POOL_MAX = 20;

export function createDb(connectionString: string, poolMax?: number) {
  const pool = new Pool({
    connectionString,
    max: poolMax ?? (parseInt(process.env.PODIUM_DB_POOL_MAX || '', 10) || DEFAULT_POOL_MAX),
  });
  return drizzle(pool, { schema });
}

export type Database = ReturnType<typeof createDb>;

export interface DbClients {
  /** Read-write primary (postgresql-cluster-rw) — use for all writes */
  rw: Database;
  /** Read-only hot standby (postgresql-cluster-ro) — use for most reads */
  ro: Database;
  /** Any replica, may lag (postgresql-cluster-r) — use for leaderboard / public listings */
  r: Database;
}

export function createDbClients(
  rwUrl: string,
  roUrl: string,
  rUrl: string,
): DbClients {
  return {
    rw: createDb(rwUrl),
    ro: createDb(roUrl),
    r: createDb(rUrl),
  };
}
