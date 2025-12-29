#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "psycopg[binary]>=3.1",
#     "django>=5.0",
# ]
# ///
"""
Bootstrap Mathesar with admin user and Podium database connection.

Runs as init container before Mathesar starts. Uses Django for password
hashing and psycopg for direct database access.

Usage:
    uv run bootstrap.py

Environment variables (from Doppler + docker-compose):
    MATHESAR_DB_HOST       - Mathesar's internal postgres host (default: mathesar-db)
    MATHESAR_DB_PORT       - Mathesar's internal postgres port (default: 5432)
    MATHESAR_DB_USER       - Mathesar's internal postgres user (default: mathesar)
    MATHESAR_DB_PASSWORD   - Mathesar's internal postgres password (from Doppler)
    MATHESAR_DB_NAME       - Mathesar's internal postgres database (default: mathesar_django)

    MATHESAR_ADMIN_USERNAME - Admin username (default: admin)
    MATHESAR_ADMIN_PASSWORD - Admin password (from Doppler)
    MATHESAR_ADMIN_EMAIL    - Admin email (default: admin@podium.hackclub.com)

    PODIUM_DATABASE_URL    - Podium postgres URL (from Doppler, same as backend uses)
                             Format: postgresql://user:pass@host:port/dbname
"""

import os
import sys
from datetime import datetime, timezone
from urllib.parse import urlparse

import psycopg
from django.contrib.auth.hashers import make_password


def get_env(key: str, default: str | None = None) -> str:
    value = os.environ.get(key, default)
    if value is None:
        print(f"✗ Missing required environment variable: {key}")
        sys.exit(1)
    return value


def main():
    # Mathesar internal DB config
    mathesar_db = {
        "host": get_env("MATHESAR_DB_HOST", "mathesar-db"),
        "port": int(get_env("MATHESAR_DB_PORT", "5432")),
        "user": get_env("MATHESAR_DB_USER", "mathesar"),
        "password": get_env("MATHESAR_DB_PASSWORD"),
        "dbname": get_env("MATHESAR_DB_NAME", "mathesar_django"),
    }

    # Admin user config
    admin_username = get_env("MATHESAR_ADMIN_USERNAME", "admin")
    admin_password = get_env("MATHESAR_ADMIN_PASSWORD")
    admin_email = get_env("MATHESAR_ADMIN_EMAIL", "admin@podium.hackclub.com")

    # Podium DB config (external connection) - parse from DATABASE_URL
    podium_url = get_env("PODIUM_DATABASE_URL")
    parsed = urlparse(podium_url)
    podium_host = parsed.hostname or "localhost"
    podium_port = parsed.port or 5432
    podium_db = parsed.path.lstrip("/") or "podium"
    podium_user = parsed.username or "postgres"
    podium_password = parsed.password or ""

    now = datetime.now(timezone.utc)

    print(f"Connecting to Mathesar DB at {mathesar_db['host']}:{mathesar_db['port']}...")

    # Wait for database to be ready
    import time
    for attempt in range(30):
        try:
            conn = psycopg.connect(**mathesar_db)
            break
        except psycopg.OperationalError:
            if attempt < 29:
                print(f"  Waiting for database... ({attempt + 1}/30)")
                time.sleep(2)
            else:
                print("✗ Could not connect to Mathesar database after 30 attempts")
                sys.exit(1)

    with conn:
        with conn.cursor() as cur:
            # 1. Create admin user
            cur.execute(
                "SELECT id FROM mathesar_user WHERE username = %s",
                (admin_username,),
            )
            if cur.fetchone():
                print(f"• Admin user already exists: {admin_username}")
            else:
                password_hash = make_password(admin_password)
                cur.execute(
                    """
                    INSERT INTO mathesar_user (
                        username, email, password, is_superuser, is_staff, is_active,
                        date_joined, password_change_needed, display_language
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (admin_username, admin_email, password_hash, True, True, True, now, False, "en"),
                )
                print(f"✓ Created admin user: {admin_username}")

            # 2. Create or get server
            cur.execute(
                "SELECT id FROM mathesar_server WHERE host = %s AND port = %s",
                (podium_host, podium_port),
            )
            row = cur.fetchone()
            if row:
                server_id = row[0]
                print(f"• Server already exists: {podium_host}:{podium_port}")
            else:
                cur.execute(
                    """
                    INSERT INTO mathesar_server (host, port, sslmode, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (podium_host, podium_port, "prefer", now, now),
                )
                server_id = cur.fetchone()[0]
                print(f"✓ Created server: {podium_host}:{podium_port}")

            # 3. Create database connection
            cur.execute(
                "SELECT id FROM mathesar_database WHERE server_id = %s AND name = %s",
                (server_id, podium_db),
            )
            if cur.fetchone():
                print(f"• Database already exists: {podium_db}")
            else:
                cur.execute(
                    """
                    INSERT INTO mathesar_database (server_id, name, nickname, last_confirmed_sql_version, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (server_id, podium_db, "Podium", "", now, now),
                )
                print(f"✓ Created database: {podium_db}")

            # 4. Create configured role (stored credentials)
            cur.execute(
                "SELECT id FROM mathesar_configuredrole WHERE server_id = %s AND name = %s",
                (server_id, podium_user),
            )
            if cur.fetchone():
                print(f"• Role already exists: {podium_user}")
            else:
                cur.execute(
                    """
                    INSERT INTO mathesar_configuredrole (server_id, name, password, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (server_id, podium_user, podium_password, now, now),
                )
                print(f"✓ Created role: {podium_user}")

        conn.commit()

    print("\n✅ Mathesar bootstrap complete!")
    print(f"   Login: {admin_username}")
    print(f"   Database: {podium_db} on {podium_host}:{podium_port}")


if __name__ == "__main__":
    main()
