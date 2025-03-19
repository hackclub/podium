from pyairtable import Api, Table

from podium import settings


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
