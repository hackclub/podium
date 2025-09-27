from pyairtable import Api, Table
from contextvars import ContextVar
from fastapi import Request
import requests
from typing import Any

from podium import settings

# Context variable to track current request
_current_request: ContextVar[Request] = ContextVar("current_request", default=None)

# Store original requests Session.request method
_original_session_request = requests.Session.request


def _tracking_session_request(self, method, url, *args, **kwargs) -> Any:
    """Monkey-patched requests.Session.request that tracks Airtable HTTP calls"""
    response = _original_session_request(self, method, url, *args, **kwargs)

    # Check if this is an Airtable API call
    if isinstance(url, str) and "api.airtable.com" in url:
        request = _current_request.get()
        if request is not None and hasattr(request, "state"):
            request.state.airtable_hits = getattr(request.state, "airtable_hits", 0) + 1

    return response


# Monkey-patch requests.Session.request to track HTTP calls
requests.Session.request = _tracking_session_request


tables: dict[str, Table] = {}


def get_table(api: Api, base_id: str, table_id: str) -> Table:
    return api.table(base_id, table_id)


def main():
    api = Api(api_key=settings.airtable_token)
    global tables
    tables["events"] = get_table(
        api, settings.airtable_base_id, settings.airtable_events_table_id
    )
    tables["users"] = get_table(
        api, settings.airtable_base_id, settings.airtable_users_table_id
    )
    tables["projects"] = get_table(
        api, settings.airtable_base_id, settings.airtable_projects_table_id
    )
    tables["referrals"] = get_table(
        api, settings.airtable_base_id, settings.airtable_referrals_table_id
    )
    tables["votes"] = get_table(
        api, settings.airtable_base_id, settings.airtable_votes_table_id
    )


main()
