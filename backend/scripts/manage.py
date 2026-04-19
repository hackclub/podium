#!/usr/bin/env python3
"""
TUI for managing Podium events and users.

Usage:
    cd backend
    doppler run --config dev -- uv run python scripts/manage.py

Keybindings:
    q           Quit
    r           Refresh data from DB
    Tab         Switch between Events / Users tabs
    n           New event  (Events tab only)
    a           Manage attendees  (Events tab only)
    d           Delete selected row
"""

import re
import sys
import traceback
from uuid import UUID

try:
    from textual import on, work
except ImportError:
    print("Error: 'textual' not found. Run this script from the backend/ directory:\n  doppler run --config dev -- uv run scripts/manage.py", file=sys.stderr)
    sys.exit(1)
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.suggester import Suggester
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    Select,
    Static,
    Switch,
    TabPane,
    TabbedContent,
)
from sqlmodel import select

sys.path.insert(0, ".")

PHASE_OPTIONS = [("Draft", "draft"), ("Submission", "submission"), ("Voting", "voting"), ("Closed", "closed")]
DEFAULT_PHASE = "submission"


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text[:50]


def get_db():
    try:
        from podium.db.postgres.base import async_session_factory
        return async_session_factory
    except Exception as e:
        print(f"Failed to import database: {e}")
        return None


def get_active_series() -> str:
    try:
        from podium.config import settings
        return settings.get("active_event_series", "") or ""
    except Exception:
        return ""


class EmailSuggester(Suggester):
    def __init__(self, emails: list[str]) -> None:
        super().__init__(use_cache=False, case_sensitive=False)
        self.emails = emails

    async def get_suggestion(self, value: str) -> str | None:
        if not value:
            return None
        value_lower = value.lower()
        for email in self.emails:
            if email.lower().startswith(value_lower) and email.lower() != value_lower:
                return email
        return None


class ConfirmDialog(ModalScreen[bool]):
    BINDINGS = [Binding("escape", "cancel", "Cancel"), Binding("enter", "confirm", "Confirm")]

    def __init__(self, message: str) -> None:
        super().__init__()
        self.message = message

    def compose(self) -> ComposeResult:
        with Container(id="confirm-dialog"):
            yield Label(self.message, id="confirm-message")
            with Horizontal(id="confirm-buttons"):
                yield Button("Cancel", variant="default", id="cancel")
                yield Button("Confirm", variant="error", id="confirm")

    @on(Button.Pressed, "#cancel")
    def action_cancel(self) -> None:
        self.dismiss(False)

    @on(Button.Pressed, "#confirm")
    def action_confirm(self) -> None:
        self.dismiss(True)


class CreateEventScreen(ModalScreen[bool]):
    """Create a new event. Only collects the fields needed to bootstrap one."""

    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def __init__(self, users: list[dict]) -> None:
        super().__init__()
        self.users = users
        self.email_suggester = EmailSuggester([u["email"] for u in users])

    def compose(self) -> ComposeResult:
        with Container(id="create-dialog"):
            yield Label("Create New Event", id="create-title")
            with VerticalScroll(id="create-form"):
                yield Label("Name *")
                yield Input(placeholder="Event name", id="name")
                yield Label("Slug (auto-generated if empty)")
                yield Input(placeholder="event-slug", id="slug")
                yield Label("Description")
                yield Input(placeholder="Description", id="description")
                yield Label("Feature Flags (comma-separated)")
                yield Input(value=get_active_series(), placeholder="scrapyard-2025", id="feature-flags")
                yield Label("Owner Email * (Tab to autocomplete)")
                yield Input(placeholder="user@example.com", id="owner-email", suggester=self.email_suggester)
                yield Label("Phase")
                yield Select(PHASE_OPTIONS, value=DEFAULT_PHASE, id="phase")
                with Horizontal(classes="switch-row"):
                    yield Label("Demo Optional")
                    yield Switch(id="demo-optional")
            with Horizontal(id="create-buttons"):
                yield Button("Cancel", variant="default", id="cancel")
                yield Button("Create", variant="success", id="create")

    def action_cancel(self) -> None:
        self.dismiss(False)

    @on(Button.Pressed, "#cancel")
    def on_cancel(self) -> None:
        self.dismiss(False)

    @on(Button.Pressed, "#create")
    async def on_create(self) -> None:
        try:
            name = self.query_one("#name", Input).value.strip()
            slug = self.query_one("#slug", Input).value.strip()
            description = self.query_one("#description", Input).value.strip()
            feature_flags = self.query_one("#feature-flags", Input).value.strip()
            owner_email = self.query_one("#owner-email", Input).value.strip().lower()
            phase_value = self.query_one("#phase", Select).value
            phase = DEFAULT_PHASE if phase_value is Select.BLANK else str(phase_value)
            demo_optional = self.query_one("#demo-optional", Switch).value

            if not name:
                self.notify("Name is required", severity="error")
                return
            if not owner_email:
                self.notify("Owner email is required", severity="error")
                return

            owner = next((u for u in self.users if u["email"].lower() == owner_email), None)
            if not owner:
                self.notify(f"User not found: {owner_email}", severity="error")
                return

            event_slug = slug or slugify(name)
            db = get_db()
            if not db:
                self.notify("Database not configured", severity="error")
                return

            from podium.db.postgres import Event

            async with db() as session:
                existing = await session.execute(select(Event).where(Event.slug == event_slug))
                if existing.scalars().first():
                    self.notify(f"Slug '{event_slug}' already exists", severity="error")
                    return

                event = Event(
                    name=name,
                    slug=event_slug,
                    description=description,
                    feature_flags_csv=feature_flags,
                    phase=phase,
                    demo_links_optional=demo_optional,
                    owner_id=owner["id"],
                )
                session.add(event)
                await session.commit()

            self.notify(f"Created: {name}")
            self.dismiss(True)
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")
            traceback.print_exc()


class ManageAttendeesScreen(ModalScreen[bool]):
    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def __init__(self, event: dict, users: list[dict]) -> None:
        super().__init__()
        self.event = event
        self.users = users
        self.attendee_ids: set[UUID] = set()
        self.email_suggester = EmailSuggester([u["email"] for u in users])

    def compose(self) -> ComposeResult:
        with Container(id="attendees-dialog"):
            yield Label(f"Attendees: {self.event['name']}", id="create-title")
            with Horizontal(id="add-attendee-row"):
                yield Input(placeholder="Add by email (Tab to autocomplete)", id="add-email", suggester=self.email_suggester)
                yield Button("Add", variant="success", id="btn-add-attendee")
            yield DataTable(id="attendees-table")
            with Horizontal(id="create-buttons"):
                yield Button("Remove Selected", variant="error", id="btn-remove-attendee")
                yield Button("Close", variant="default", id="close")

    async def on_mount(self) -> None:
        await self.load_attendees()

    async def load_attendees(self) -> None:
        try:
            db = get_db()
            if not db:
                return
            from podium.db.postgres.links import EventAttendeeLink

            async with db() as session:
                result = await session.execute(
                    select(EventAttendeeLink).where(EventAttendeeLink.event_id == self.event["id"])
                )
                self.attendee_ids = {link.user_id for link in result.scalars().all()}
            self.refresh_table()
        except Exception as e:
            self.notify(f"Error loading attendees: {e}", severity="error")
            traceback.print_exc()

    def refresh_table(self) -> None:
        table = self.query_one("#attendees-table", DataTable)
        table.clear(columns=True)
        table.add_columns("Email", "Name")
        table.cursor_type = "row"
        for user in self.users:
            if user["id"] in self.attendee_ids:
                name = user.get("display_name") or f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
                table.add_row(user["email"][:35], name[:25], key=str(user["id"]))

    def get_selected_user(self) -> dict | None:
        try:
            table = self.query_one("#attendees-table", DataTable)
            if table.row_count == 0:
                return None
            row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
            uid = str(row_key.value) if row_key else None
            return next((u for u in self.users if str(u["id"]) == uid), None)
        except Exception:
            return None

    def action_cancel(self) -> None:
        self.dismiss(True)

    @on(Button.Pressed, "#close")
    def on_close(self) -> None:
        self.dismiss(True)

    @on(Button.Pressed, "#btn-add-attendee")
    async def on_add_attendee(self) -> None:
        email = self.query_one("#add-email", Input).value.strip().lower()
        if not email:
            self.notify("Enter an email", severity="warning")
            return
        user = next((u for u in self.users if u["email"].lower() == email), None)
        if not user:
            self.notify(f"User not found: {email}", severity="error")
            return
        if user["id"] in self.attendee_ids:
            self.notify(f"{email} is already an attendee", severity="warning")
            return
        try:
            db = get_db()
            if not db:
                return
            from podium.db.postgres.links import EventAttendeeLink

            async with db() as session:
                session.add(EventAttendeeLink(event_id=self.event["id"], user_id=user["id"]))
                await session.commit()
            self.attendee_ids.add(user["id"])
            self.refresh_table()
            self.query_one("#add-email", Input).value = ""
            self.notify(f"Added: {email}")
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")
            traceback.print_exc()

    @on(Button.Pressed, "#btn-remove-attendee")
    async def on_remove_attendee(self) -> None:
        user = self.get_selected_user()
        if not user:
            self.notify("Select an attendee first", severity="warning")
            return
        try:
            db = get_db()
            if not db:
                return
            from podium.db.postgres.links import EventAttendeeLink

            async with db() as session:
                result = await session.execute(
                    select(EventAttendeeLink).where(
                        EventAttendeeLink.event_id == self.event["id"],
                        EventAttendeeLink.user_id == user["id"],
                    )
                )
                link = result.scalars().first()
                if link:
                    await session.delete(link)
                    await session.commit()
            self.attendee_ids.discard(user["id"])
            self.refresh_table()
            self.notify(f"Removed: {user['email']}")
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")
            traceback.print_exc()


class EventManagerApp(App):
    """TUI for managing Podium events and users."""

    TITLE = "Podium Admin"

    CSS = """
    #confirm-dialog, #create-dialog {
        align: center middle;
        width: 60;
        height: auto;
        max-height: 80%;
        background: $surface;
        border: solid $primary;
        padding: 1 2;
    }
    #confirm-dialog { width: 50; max-height: 12; }
    #confirm-message, #create-title {
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
    }
    #confirm-buttons, #create-buttons {
        align: center middle;
        height: 3;
        margin-top: 1;
    }
    #confirm-buttons Button, #create-buttons Button { margin: 0 1; }
    #create-form { height: auto; max-height: 20; }
    #create-form Label { margin-top: 1; }
    .switch-row { height: 3; align: left middle; }
    .switch-row Label { width: 20; margin-top: 0; }
    .switch-row Switch { margin-left: 1; }
    #filter-row { height: 3; margin: 1 0; }
    #filter-row Label { width: auto; margin-right: 1; }
    #action-buttons { height: 3; margin: 1 0; align: left middle; }
    #action-buttons Button { margin-right: 1; }
    #status-bar { height: 1; background: $primary-background; color: $text; padding: 0 1; }
    DataTable { height: 1fr; }
    #attendees-dialog {
        align: center middle;
        width: 70;
        height: auto;
        max-height: 80%;
        background: $surface;
        border: solid $primary;
        padding: 1 2;
    }
    #add-attendee-row { height: 3; margin-bottom: 1; }
    #add-attendee-row Input { width: 1fr; margin-right: 1; }
    #attendees-table { height: 15; }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", priority=True),
        Binding("ctrl+c", "quit", "Quit", show=False, priority=True),
        Binding("r", "refresh", "Refresh", priority=True),
        Binding("n", "new_event", "New Event", priority=True),
        Binding("a", "manage_attendees", "Attendees", priority=True),
        Binding("d", "delete_item", "Delete", priority=True),
        Binding("ctrl+left_square_bracket", "prev_tab", "Prev Tab", show=False),
        Binding("ctrl+right_square_bracket", "next_tab", "Next Tab", show=False),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.events: list[dict] = []
        self.users: list[dict] = []
        self.filter_text = ""
        self.db_error: str | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent():
            with TabPane("Events", id="events-tab"):
                with Vertical():
                    with Horizontal(id="filter-row"):
                        yield Label("Filter:")
                        yield Input(placeholder="Search by name, slug, or flags...", id="filter-input")
                    with Horizontal(id="action-buttons"):
                        yield Button("New (n)", variant="success", id="btn-new")
                        yield Button("Attendees (a)", variant="primary", id="btn-attendees")
                        yield Button("Delete (d)", variant="error", id="btn-delete")
                        yield Button("Refresh (r)", variant="default", id="btn-refresh")
                    yield DataTable(id="events-table")
            with TabPane("Users", id="users-tab"):
                with Vertical():
                    with Horizontal(id="filter-row"):
                        yield Label("Filter:")
                        yield Input(placeholder="Search by email or name...", id="user-filter-input")
                    with Horizontal(id="action-buttons"):
                        yield Button("Toggle Superadmin", variant="warning", id="btn-toggle-superadmin")
                        yield Button("Delete (d)", variant="error", id="btn-delete-user")
                        yield Button("Refresh (r)", variant="default", id="btn-refresh-users")
                    yield DataTable(id="users-table")
        yield Static("Loading...", id="status-bar")
        yield Footer()

    async def on_mount(self) -> None:
        self.load_data()

    def get_active_tab(self) -> str:
        try:
            return self.query_one(TabbedContent).active or "events-tab"
        except Exception:
            return "events-tab"

    def action_prev_tab(self) -> None:
        try:
            tabbed = self.query_one(TabbedContent)
            tabbed.active = "users-tab" if self.get_active_tab() == "events-tab" else "events-tab"
        except Exception:
            pass

    def action_next_tab(self) -> None:
        self.action_prev_tab()

    def on_tabbed_content_tab_activated(self, _: TabbedContent.TabActivated) -> None:
        self.refresh_bindings()

    def check_action(self, action: str, parameters: tuple) -> bool | None:
        if action in ("new_event", "manage_attendees") and self.get_active_tab() != "events-tab":
            return False
        return True

    @work(exclusive=True)
    async def load_data(self) -> None:
        self.query_one("#status-bar", Static).update("Loading...")
        try:
            db = get_db()
            if not db:
                self.db_error = "Database not configured. Run with: doppler run --config dev -- uv run python scripts/manage.py"
                self.query_one("#status-bar", Static).update(f"ERROR: {self.db_error}")
                self.notify(self.db_error, title="No database connection", severity="error", timeout=30)
                return

            from podium.db.postgres import Event, User

            async with db() as session:
                events_rows = await session.scalars(select(Event))
                self.events = [
                    {**e.__dict__, "id": e.id, "owner_id": e.owner_id}
                    for e in events_rows.all()
                ]
                users_rows = await session.scalars(select(User))
                self.users = [
                    {**u.__dict__, "id": u.id}
                    for u in users_rows.all()
                ]

            self.refresh_events_table()
            self.refresh_users_table()
            self.query_one("#status-bar", Static).update(
                f"Loaded {len(self.events)} events, {len(self.users)} users"
            )
            self.db_error = None
        except Exception as e:
            self.db_error = str(e)
            self.query_one("#status-bar", Static).update(f"ERROR: {e}")
            self.notify(str(e), title="Load failed", severity="error", timeout=10)
            traceback.print_exc()

    def refresh_events_table(self) -> None:
        try:
            table = self.query_one("#events-table", DataTable)
            table.clear(columns=True)
            table.add_columns("Name", "Slug", "Phase", "Feature Flags", "Owner")
            table.cursor_type = "row"
            f = self.filter_text.lower()
            for event in self.events:
                name = event.get("name", "")
                slug = event.get("slug", "")
                flags = event.get("feature_flags_csv", "")
                if f and not any(f in s.lower() for s in [name, slug, flags]):
                    continue
                owner = next((u for u in self.users if u["id"] == event.get("owner_id")), None)
                table.add_row(
                    name[:30], slug[:25], event.get("phase", ""), flags,
                    (owner["email"] if owner else "")[:25],
                    key=str(event["id"]),
                )
        except Exception as e:
            self.notify(f"Error refreshing events: {e}", severity="error")

    def refresh_users_table(self) -> None:
        try:
            table = self.query_one("#users-table", DataTable)
            table.clear(columns=True)
            table.add_columns("Email", "Name", "Superadmin")
            table.cursor_type = "row"
            f = ""
            try:
                f = self.query_one("#user-filter-input", Input).value.lower()
            except Exception:
                pass
            for user in self.users:
                email = user.get("email", "")
                name = user.get("display_name") or f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
                if f and not any(f in s.lower() for s in [email, name]):
                    continue
                table.add_row(
                    email[:40], name[:30],
                    "✓" if user.get("is_superadmin") else "",
                    key=str(user["id"]),
                )
        except Exception as e:
            self.notify(f"Error refreshing users: {e}", severity="error")

    def get_selected_event(self) -> dict | None:
        try:
            table = self.query_one("#events-table", DataTable)
            if table.row_count == 0:
                return None
            row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
            eid = str(row_key.value) if row_key else None
            return next((e for e in self.events if str(e["id"]) == eid), None)
        except Exception:
            return None

    def get_selected_user(self) -> dict | None:
        try:
            table = self.query_one("#users-table", DataTable)
            if table.row_count == 0:
                return None
            row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
            uid = str(row_key.value) if row_key else None
            return next((u for u in self.users if str(u["id"]) == uid), None)
        except Exception:
            return None

    @on(Input.Changed, "#filter-input")
    def on_filter_changed(self, event: Input.Changed) -> None:
        self.filter_text = event.value
        self.refresh_events_table()

    @on(Input.Changed, "#user-filter-input")
    def on_user_filter_changed(self, _: Input.Changed) -> None:
        self.refresh_users_table()

    @on(Button.Pressed, "#btn-refresh")
    @on(Button.Pressed, "#btn-refresh-users")
    def action_refresh(self) -> None:
        self.load_data()
        self.notify("Refreshing...")

    def action_new_event(self) -> None:
        if self.get_active_tab() != "events-tab":
            return
        if self.db_error:
            self.notify("Database not connected", severity="error")
            return
        self.push_screen(CreateEventScreen(self.users), lambda ok: self.load_data() if ok else None)

    @on(Button.Pressed, "#btn-new")
    def on_btn_new(self) -> None:
        self.action_new_event()

    def action_manage_attendees(self) -> None:
        if self.get_active_tab() != "events-tab":
            return
        event = self.get_selected_event()
        if not event:
            self.notify("Select an event first", severity="warning")
            return
        self.push_screen(ManageAttendeesScreen(event, self.users), lambda _: None)

    @on(Button.Pressed, "#btn-attendees")
    def on_btn_attendees(self) -> None:
        self.action_manage_attendees()

    def action_delete_item(self) -> None:
        if self.get_active_tab() == "users-tab":
            self._prompt_delete_user()
        else:
            self._prompt_delete_event()

    def _prompt_delete_event(self) -> None:
        event = self.get_selected_event()
        if not event:
            self.notify("Select an event first", severity="warning")
            return
        self.push_screen(
            ConfirmDialog(f"Delete '{event['name']}'?"),
            lambda ok: self._do_delete_event(event, ok),
        )

    @work(exclusive=True)
    async def _do_delete_event(self, event: dict, confirmed: bool) -> None:
        if not confirmed:
            return
        try:
            db = get_db()
            if not db:
                return
            from podium.db.postgres import Event

            async with db() as session:
                db_event = await session.get(Event, event["id"])
                if db_event:
                    await session.delete(db_event)
                    await session.commit()
            self.notify(f"Deleted: {event['name']}")
            self.load_data()
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")
            traceback.print_exc()

    @on(Button.Pressed, "#btn-delete")
    def on_btn_delete_event(self) -> None:
        self._prompt_delete_event()

    @on(Button.Pressed, "#btn-toggle-superadmin")
    def on_toggle_superadmin(self) -> None:
        user = self.get_selected_user()
        if not user:
            self.notify("Select a user first", severity="warning")
            return
        action = "revoke" if user.get("is_superadmin") else "grant"
        self.push_screen(
            ConfirmDialog(f"{action.capitalize()} superadmin for '{user['email']}'?"),
            lambda ok: self._do_toggle_superadmin(user, ok),
        )

    @work(exclusive=True)
    async def _do_toggle_superadmin(self, user: dict, confirmed: bool) -> None:
        if not confirmed:
            return
        try:
            db = get_db()
            if not db:
                return
            from podium.db.postgres import User

            async with db() as session:
                db_user = await session.get(User, user["id"])
                if not db_user:
                    self.notify("User not found", severity="error")
                    return
                db_user.is_superadmin = not db_user.is_superadmin
                await session.commit()
                new_state = db_user.is_superadmin
            self.notify(f"Superadmin {'granted' if new_state else 'revoked'} for {user['email']}")
            self.load_data()
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")
            traceback.print_exc()

    def _prompt_delete_user(self) -> None:
        user = self.get_selected_user()
        if not user:
            self.notify("Select a user first", severity="warning")
            return
        self.push_screen(
            ConfirmDialog(f"Delete '{user['email']}'?\nAlso deletes their events, projects, and votes."),
            lambda ok: self._do_delete_user(user, ok),
        )

    @on(Button.Pressed, "#btn-delete-user")
    def on_btn_delete_user(self) -> None:
        self._prompt_delete_user()

    @work(exclusive=True)
    async def _do_delete_user(self, user: dict, confirmed: bool) -> None:
        if not confirmed:
            return
        try:
            db = get_db()
            if not db:
                return
            from podium.db.postgres import User

            async with db() as session:
                db_user = await session.get(User, user["id"])
                if db_user:
                    await session.delete(db_user)
                    await session.commit()
            self.notify(f"Deleted: {user['email']}")
            self.load_data()
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")
            traceback.print_exc()


def main() -> None:
    try:
        EventManagerApp().run()
    except Exception as e:
        print(f"Fatal error: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
