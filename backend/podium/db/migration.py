# python -m podium.db.migration | Tee-Object -FilePath migration.txt                                                                                
# $env:PYTHON_ENV="production"                                                                               
# $env:PYTHONIOENCODING="utf-8"
from podium.db import users
from podium.db.user import UserPrivate, UserSignupPayload
import rich

def add_display_names(): 
    for records in users.iterate(page_size=100):
        for record in records:
            user = UserPrivate.model_validate(record["fields"])
            if user.display_name:
                continue
            user.display_name = f"{user.first_name} {user.last_name[0]}." if user.last_name else user.first_name
            rich.print(users.update(user.id, UserSignupPayload.model_validate(user.model_dump()).model_dump())["fields"])
            print(f"Updated {user.id} with display name: {user.display_name} ({user.first_name} {user.last_name})")


def main():
    print("Starting migration to add display names...")
    add_display_names()
    print("Migration completed.")

if __name__ == "__main__":
    main()