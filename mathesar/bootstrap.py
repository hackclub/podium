#!/usr/bin/env python
"""
Bootstrap Mathesar with admin user and Podium database connection.

Runs on container startup before Mathesar. Uses Mathesar's Django environment.
Secrets are injected by Doppler via environment variables.

Environment variables (from Doppler):
    MATHESAR_ADMIN_USERNAME - Admin username (default: admin)
    MATHESAR_ADMIN_PASSWORD - Admin password (required)
    MATHESAR_ADMIN_EMAIL    - Admin email (default: admin@podium.hackclub.com)
    PODIUM_DATABASE_URL     - Podium postgres URL (required)
    POSTGRES_PASSWORD       - Internal DB password (injected by Doppler)
"""

import os
import sys

# Setup Django before importing models
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

import django
django.setup()

from urllib.parse import urlparse
from django.contrib.auth import get_user_model
from django.apps import apps
from django.utils import timezone


def get_env(key: str, default: str | None = None) -> str:
    value = os.environ.get(key, default)
    if value is None:
        print(f"✗ Missing required environment variable: {key}")
        sys.exit(1)
    return value


def main():
    User = get_user_model()
    
    # Check if admin already exists
    admin_username = get_env("MATHESAR_ADMIN_USERNAME", "admin")
    if User.objects.filter(username=admin_username).exists():
        print(f"• Admin user '{admin_username}' already exists, skipping bootstrap")
        return
    
    # Get config from environment
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
    
    now = timezone.now()
    
    # 1. Create admin user
    print(f"Creating admin user: {admin_username}")
    user = User.objects.create_superuser(
        username=admin_username,
        email=admin_email,
        password=admin_password,
    )
    # Mark password change not needed
    user.password_change_needed = False
    user.save()
    print(f"✓ Created admin user: {admin_username}")
    
    # 2. Create server connection for Podium
    Server = apps.get_model("mathesar", "Server")
    server, created = Server.objects.get_or_create(
        host=podium_host,
        port=podium_port,
        defaults={
            "sslmode": "prefer",
        }
    )
    if created:
        print(f"✓ Created server: {podium_host}:{podium_port}")
    else:
        print(f"• Server already exists: {podium_host}:{podium_port}")
    
    # 3. Create database connection
    Database = apps.get_model("mathesar", "Database")
    database, created = Database.objects.get_or_create(
        server=server,
        name=podium_db,
        defaults={
            "nickname": "Podium",
        }
    )
    if created:
        print(f"✓ Created database: {podium_db}")
    else:
        print(f"• Database already exists: {podium_db}")
    
    # 4. Create configured role (stored credentials)
    ConfiguredRole = apps.get_model("mathesar", "ConfiguredRole")
    role, created = ConfiguredRole.objects.get_or_create(
        server=server,
        name=podium_user,
        defaults={
            "password": podium_password,
        }
    )
    if created:
        print(f"✓ Created role: {podium_user}")
    else:
        print(f"• Role already exists: {podium_user}")
    
    print("\n✅ Mathesar bootstrap complete!")
    print(f"   Login: {admin_username}")
    print(f"   Database: {podium_db} on {podium_host}:{podium_port}")


if __name__ == "__main__":
    main()
