#!/usr/bin/env python
"""
Bootstrap Mathesar with admin user and Podium database connection.

Runs on container startup. Idempotent - safe to run multiple times.
Always ensures database connection is configured and SQL is upgraded.

Environment variables:
    MATHESAR_ADMIN_USERNAME - Admin username (default: admin)
    MATHESAR_ADMIN_PASSWORD - Admin password (required)
    MATHESAR_ADMIN_EMAIL    - Admin email (default: admin@podium.hackclub.com)
    PODIUM_DATABASE_URL     - Podium postgres URL (required)
"""

import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

import django
django.setup()

from urllib.parse import urlparse
from django.contrib.auth import get_user_model
from django.apps import apps


def get_env(key: str, default: str | None = None) -> str:
    value = os.environ.get(key, default)
    if value is None:
        print(f"✗ Missing required environment variable: {key}")
        sys.exit(1)
    return value


def main():
    User = get_user_model()
    Server = apps.get_model("mathesar", "Server")
    Database = apps.get_model("mathesar", "Database")
    ConfiguredRole = apps.get_model("mathesar", "ConfiguredRole")
    UserDatabaseRoleMap = apps.get_model("mathesar", "UserDatabaseRoleMap")

    admin_username = get_env("MATHESAR_ADMIN_USERNAME", "admin")
    admin_password = get_env("MATHESAR_ADMIN_PASSWORD")
    admin_email = get_env("MATHESAR_ADMIN_EMAIL", "admin@podium.hackclub.com")

    # Parse Podium database URL
    podium_url = get_env("PODIUM_DATABASE_URL")
    parsed = urlparse(podium_url)
    podium_host = parsed.hostname or "localhost"
    podium_port = parsed.port or 5432
    podium_db = parsed.path.lstrip("/") or "podium"
    podium_user = parsed.username or "postgres"
    podium_password = parsed.password or ""

    # 1. Create or get admin user
    user, created = User.objects.get_or_create(
        username=admin_username,
        defaults={"email": admin_email, "is_superuser": True, "is_staff": True}
    )
    if created:
        user.set_password(admin_password)
        user.password_change_needed = False
        user.save()
        print(f"✓ Created admin user: {admin_username}")
    else:
        print(f"• Admin user exists: {admin_username}")

    # 2. Create or update server
    server, created = Server.objects.update_or_create(
        host=podium_host,
        port=podium_port,
        defaults={}
    )
    print(f"{'✓ Created' if created else '•'} Server: {podium_host}:{podium_port}")

    # 3. Create or get database
    database, created = Database.objects.get_or_create(
        server=server,
        name=podium_db,
        defaults={"nickname": "Podium"}
    )
    print(f"{'✓ Created' if created else '•'} Database: {podium_db}")

    # 4. Create or UPDATE role (always update password)
    role, created = ConfiguredRole.objects.update_or_create(
        server=server,
        name=podium_user,
        defaults={"password": podium_password}
    )
    print(f"{'✓ Created' if created else '✓ Updated'} Role: {podium_user}")

    # 5. Link user to database
    mapping, created = UserDatabaseRoleMap.objects.get_or_create(
        user=user,
        database=database,
        defaults={"configured_role": role, "server": server}
    )
    if not created:
        # Update role if it changed
        mapping.configured_role = role
        mapping.save()
    print(f"{'✓ Created' if created else '•'} User-database link")

    # 6. Install/upgrade Mathesar SQL in target database
    print("Installing Mathesar SQL...")
    try:
        database.install_sql(username=podium_user, password=podium_password)
        print("✓ Mathesar SQL installed")
    except Exception as e:
        print(f"⚠ SQL install skipped: {e}")

    print(f"\n✅ Bootstrap complete! Database: {podium_db} on {podium_host}:{podium_port}")


if __name__ == "__main__":
    main()
