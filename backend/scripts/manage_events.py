#!/usr/bin/env python3
"""
TUI for managing events in the database.

Events can no longer be created via UI, so use this tool for admin operations.

Usage:
    cd backend
    doppler run --config dev -- uv run python scripts/manage_events.py
"""

import re
import sys
import traceback
from dataclasses import dataclass
from secrets import token_urlsafe
from uuid import UUID

from textual import on, work
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
    Static,
    Switch,
    TabPane,
    TabbedContent,
)
from sqlmodel import select

# Add parent to path for imports
sys.path.insert(0, ".")


@dataclass
class EventData:
    """Simple dataclass to hold event data outside of SQLAlchemy session."""
    id: UUID
    name: str
    slug: str
    description: str
    feature_flags_csv: str
    votable: bool
    leaderboard_enabled: bool
    demo_links_optional: bool
    owner_id: UUID


@dataclass
class UserData:
    """Simple dataclass to hold user data outside of SQLAlchemy session."""
    id: UUID
    email: str
    display_name: str
    first_name: str
    last_name: str


def slugify(text: str) -> str:
    """Convert text to URL-safe slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text[:50]


def get_db_connection():
    """Import and return database connection. Returns None if not configured."""
    try:
        from podium.db.postgres.base import async_session_factory
        return async_session_factory
    except Exception as e:
        print(f"Failed to import database: {e}")
        return None


def get_active_series() -> str:
    """Get the active event series from settings."""
    try:
        from podium.config import settings
        return settings.get("active_event_series", "") or ""
    except Exception:
        return ""


class EmailSuggester(Suggester):
    """Suggester for user emails."""

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
    """Modal confirmation dialog."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("enter", "confirm", "Confirm"),
    ]

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


class CreateEventScreen(ModalScreen[EventData | None]):
    """Modal for creating a new event."""

    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def __init__(self, users: list[UserData]) -> None:
        super().__init__()
        self.users = users
        self.default_series = get_active_series()
        self.email_suggester = EmailSuggester([u.email for u in users])

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
                yield Input(value=self.default_series, placeholder="scrapyard-2025", id="feature-flags")
                yield Label("Owner Email * (Tab to autocomplete)")
                yield Input(placeholder="user@example.com", id="owner-email", suggester=self.email_suggester)
                with Horizontal(classes="switch-row"):
                    yield Label("Votable")
                    yield Switch(id="votable")
                with Horizontal(classes="switch-row"):
                    yield Label("Leaderboard")
                    yield Switch(id="leaderboard")
                with Horizontal(classes="switch-row"):
                    yield Label("Demo Optional")
                    yield Switch(id="demo-optional")
            with Horizontal(id="create-buttons"):
                yield Button("Cancel", variant="default", id="cancel")
                yield Button("Create", variant="success", id="create")

    def action_cancel(self) -> None:
        self.dismiss(None)

    @on(Button.Pressed, "#cancel")
    def on_cancel(self) -> None:
        self.dismiss(None)

    @on(Button.Pressed, "#create")
    async def on_create(self) -> None:
        try:
            name = self.query_one("#name", Input).value.strip()
            slug = self.query_one("#slug", Input).value.strip()
            description = self.query_one("#description", Input).value.strip()
            feature_flags = self.query_one("#feature-flags", Input).value.strip()
            owner_email = self.query_one("#owner-email", Input).value.strip().lower()
            votable = self.query_one("#votable", Switch).value
            leaderboard = self.query_one("#leaderboard", Switch).value
            demo_optional = self.query_one("#demo-optional", Switch).value

            if not name:
                self.notify("Name is required", severity="error")
                return

            if not owner_email:
                self.notify("Owner email is required", severity="error")
                return

            # Find owner
            owner = next((u for u in self.users if u.email.lower() == owner_email), None)
            if not owner:
                self.notify(f"User not found: {owner_email}", severity="error")
                return

            event_slug = slug or slugify(name)

            async_session_factory = get_db_connection()
            if not async_session_factory:
                self.notify("Database not configured", severity="error")
                return

            from podium.db.postgres import Event

            async with async_session_factory() as session:
                # Check slug uniqueness
                result = await session.execute(select(Event).where(Event.slug == event_slug))
                existing = result.scalars().first()
                if existing:
                    self.notify(f"Slug '{event_slug}' already exists", severity="error")
                    return

                event = Event(
                    name=name,
                    slug=event_slug,
                    description=description,
                    join_code=token_urlsafe(6)[:8],
                    feature_flags_csv=feature_flags,
                    votable=votable,
                    leaderboard_enabled=leaderboard,
                    demo_links_optional=demo_optional,
                    owner_id=owner.id,
                )
                session.add(event)
                await session.commit()
                await session.refresh(event)

                # Convert to dataclass before session closes
                event_data = EventData(
                    id=event.id,
                    name=event.name,
                    slug=event.slug,
                    description=event.description or "",
                    feature_flags_csv=event.feature_flags_csv or "",
                    votable=event.votable,
                    leaderboard_enabled=event.leaderboard_enabled,
                    demo_links_optional=event.demo_links_optional,
                    owner_id=event.owner_id,
                )

            self.dismiss(event_data)
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")
            traceback.print_exc()


class ManageAttendeesScreen(ModalScreen[bool]):
    """Modal for managing event attendees."""

    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def __init__(self, event: EventData, users: list[UserData]) -> None:
        super().__init__()
        self.event = event
        self.users = users
        self.attendee_ids: set[UUID] = set()
        self.email_suggester = EmailSuggester([u.email for u in users])

    def compose(self) -> ComposeResult:
        with Container(id="attendees-dialog"):
            yield Label(f"Attendees: {self.event.name}", id="create-title")
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
            async_session_factory = get_db_connection()
            if not async_session_factory:
                self.notify("Database not configured", severity="error")
                return

            from podium.db.postgres.links import EventAttendeeLink

            async with async_session_factory() as session:
                result = await session.execute(
                    select(EventAttendeeLink).where(EventAttendeeLink.event_id == self.event.id)
                )
                links = result.scalars().all()
                self.attendee_ids = {link.user_id for link in links}

            self.refresh_attendees_table()
        except Exception as e:
            self.notify(f"Error loading attendees: {e}", severity="error")
            traceback.print_exc()

    def refresh_attendees_table(self) -> None:
        table = self.query_one("#attendees-table", DataTable)
        table.clear(columns=True)
        table.add_columns("Email", "Name")
        table.cursor_type = "row"

        for user in self.users:
            if user.id in self.attendee_ids:
                name = user.display_name or f"{user.first_name} {user.last_name}".strip()
                table.add_row(user.email[:35], name[:25], key=str(user.id))

    def get_selected_attendee(self) -> UserData | None:
        try:
            table = self.query_one("#attendees-table", DataTable)
            if table.row_count == 0:
                return None
            row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
            if row_key is None:
                return None
            user_id = str(row_key.value)
            return next((u for u in self.users if str(u.id) == user_id), None)
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

        user = next((u for u in self.users if u.email.lower() == email), None)
        if not user:
            self.notify(f"User not found: {email}", severity="error")
            return

        if user.id in self.attendee_ids:
            self.notify(f"{email} is already an attendee", severity="warning")
            return

        try:
            async_session_factory = get_db_connection()
            if not async_session_factory:
                return

            from podium.db.postgres.links import EventAttendeeLink

            async with async_session_factory() as session:
                link = EventAttendeeLink(event_id=self.event.id, user_id=user.id)
                session.add(link)
                await session.commit()

            self.attendee_ids.add(user.id)
            self.refresh_attendees_table()
            self.query_one("#add-email", Input).value = ""
            self.notify(f"Added: {email}")
        except Exception as e:
            self.notify(f"Error adding attendee: {e}", severity="error")
            traceback.print_exc()

    @on(Button.Pressed, "#btn-remove-attendee")
    async def on_remove_attendee(self) -> None:
        user = self.get_selected_attendee()
        if not user:
            self.notify("Select an attendee first", severity="warning")
            return

        try:
            async_session_factory = get_db_connection()
            if not async_session_factory:
                return

            from podium.db.postgres.links import EventAttendeeLink

            async with async_session_factory() as session:
                result = await session.execute(
                    select(EventAttendeeLink).where(
                        EventAttendeeLink.event_id == self.event.id,
                        EventAttendeeLink.user_id == user.id
                    )
                )
                link = result.scalars().first()
                if link:
                    await session.delete(link)
                    await session.commit()

            self.attendee_ids.discard(user.id)
            self.refresh_attendees_table()
            self.notify(f"Removed: {user.email}")
        except Exception as e:
            self.notify(f"Error removing attendee: {e}", severity="error")
            traceback.print_exc()


class EditEventScreen(ModalScreen[bool]):
    """Modal for editing an event."""

    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def __init__(self, event: EventData) -> None:
        super().__init__()
        self.event = event

    def compose(self) -> ComposeResult:
        with Container(id="create-dialog"):
            yield Label(f"Edit: {self.event.name}", id="create-title")
            with VerticalScroll(id="create-form"):
                yield Label("Name")
                yield Input(value=self.event.name, id="name")
                yield Label("Description")
                yield Input(value=self.event.description or "", id="description")
                yield Label("Feature Flags")
                yield Input(value=self.event.feature_flags_csv or "", id="feature-flags")
                with Horizontal(classes="switch-row"):
                    yield Label("Votable")
                    yield Switch(value=self.event.votable, id="votable")
                with Horizontal(classes="switch-row"):
                    yield Label("Leaderboard")
                    yield Switch(value=self.event.leaderboard_enabled, id="leaderboard")
                with Horizontal(classes="switch-row"):
                    yield Label("Demo Optional")
                    yield Switch(value=self.event.demo_links_optional, id="demo-optional")
            with Horizontal(id="create-buttons"):
                yield Button("Cancel", variant="default", id="cancel")
                yield Button("Save", variant="success", id="save")

    def action_cancel(self) -> None:
        self.dismiss(False)

    @on(Button.Pressed, "#cancel")
    def on_cancel(self) -> None:
        self.dismiss(False)

    @on(Button.Pressed, "#save")
    async def on_save(self) -> None:
        try:
            async_session_factory = get_db_connection()
            if not async_session_factory:
                self.notify("Database not configured", severity="error")
                self.dismiss(False)
                return

            from podium.db.postgres import Event

            async with async_session_factory() as session:
                event = await session.get(Event, self.event.id)
                if not event:
                    self.notify("Event not found", severity="error")
                    self.dismiss(False)
                    return

                event.name = self.query_one("#name", Input).value.strip()
                event.description = self.query_one("#description", Input).value.strip()
                event.feature_flags_csv = self.query_one("#feature-flags", Input).value.strip()
                event.votable = self.query_one("#votable", Switch).value
                event.leaderboard_enabled = self.query_one("#leaderboard", Switch).value
                event.demo_links_optional = self.query_one("#demo-optional", Switch).value

                session.add(event)
                await session.commit()

            self.dismiss(True)
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")
            traceback.print_exc()
            self.dismiss(False)


class EventManagerApp(App):
    """TUI for managing Podium events."""

    CSS = """
    #confirm-dialog {
        align: center middle;
        width: 50;
        height: auto;
        max-height: 12;
        background: $surface;
        border: solid $primary;
        padding: 1 2;
    }
    #confirm-message {
        text-align: center;
        margin-bottom: 1;
    }
    #confirm-buttons {
        align: center middle;
        height: 3;
    }
    #confirm-buttons Button {
        margin: 0 1;
    }

    #create-dialog {
        align: center middle;
        width: 60;
        height: auto;
        max-height: 80%;
        background: $surface;
        border: solid $primary;
        padding: 1 2;
    }
    #create-title {
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
    }
    #create-form {
        height: auto;
        max-height: 20;
    }
    #create-form Label {
        margin-top: 1;
    }
    #create-buttons {
        align: center middle;
        height: 3;
        margin-top: 1;
    }
    #create-buttons Button {
        margin: 0 1;
    }
    .switch-row {
        height: 3;
        align: left middle;
    }
    .switch-row Label {
        width: 20;
        margin-top: 0;
    }
    .switch-row Switch {
        margin-left: 1;
    }

    #filter-row {
        height: 3;
        margin: 1 0;
    }
    #filter-row Label {
        width: auto;
        margin-right: 1;
    }
    #filter-input {
        width: 30;
    }

    #action-buttons {
        height: 3;
        margin: 1 0;
        align: left middle;
    }
    #action-buttons Button {
        margin-right: 1;
    }

    #status-bar {
        height: 1;
        background: $primary-background;
        color: $text;
        padding: 0 1;
    }

    #hotkey-bar {
        height: 1;
        background: $surface;
        color: $text-muted;
        padding: 0 1;
        text-align: center;
    }

    DataTable {
        height: 1fr;
    }

    #error-container {
        align: center middle;
        width: 100%;
        height: 100%;
    }
    #error-message {
        text-align: center;
        color: $error;
        padding: 2;
    }

    #attendees-dialog {
        align: center middle;
        width: 70;
        height: auto;
        max-height: 80%;
        background: $surface;
        border: solid $primary;
        padding: 1 2;
    }
    #add-attendee-row {
        height: 3;
        margin-bottom: 1;
    }
    #add-attendee-row Input {
        width: 1fr;
        margin-right: 1;
    }
    #attendees-table {
        height: 15;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("ctrl+c", "quit", "Quit", show=False),
        Binding("r", "refresh", "Refresh"),
        Binding("n", "new_item", "New"),
        Binding("e", "edit_item", "Edit"),
        Binding("d", "delete_item", "Delete"),
        Binding("a", "manage_attendees", "Attendees"),
        Binding("ctrl+left_square_bracket", "prev_tab", "Prev Tab", show=False),
        Binding("ctrl+right_square_bracket", "next_tab", "Next Tab", show=False),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.events: list[EventData] = []
        self.users: list[UserData] = []
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
                        yield Button("New Event (n)", variant="success", id="btn-new")
                        yield Button("Edit (e)", variant="primary", id="btn-edit")
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
                        yield Button("Delete User", variant="error", id="btn-delete-user")
                    yield DataTable(id="users-table")
        yield Static("Loading...", id="status-bar")
        yield Static("", id="hotkey-bar")
        yield Footer()

    async def on_mount(self) -> None:
        self.load_data_async()
        self.update_hotkey_bar()

    @on(TabbedContent.TabActivated)
    def on_tab_changed(self, event: TabbedContent.TabActivated) -> None:
        """Update hotkey hints when tab changes."""
        self.update_hotkey_bar()

    def update_hotkey_bar(self) -> None:
        """Update the hotkey bar based on active tab."""
        try:
            bar = self.query_one("#hotkey-bar", Static)
            if self.get_active_tab() == "users-tab":
                bar.update("[d] Delete User  [r] Refresh  [q] Quit  [Ctrl+[/]] Switch Tabs")
            else:
                bar.update("[n] New  [e] Edit  [a] Attendees  [d] Delete  [r] Refresh  [q] Quit  [Ctrl+[/]] Tabs")
        except Exception:
            pass

    def action_prev_tab(self) -> None:
        """Switch to previous tab."""
        try:
            tabbed = self.query_one(TabbedContent)
            if self.get_active_tab() == "users-tab":
                tabbed.active = "events-tab"
            else:
                tabbed.active = "users-tab"
        except Exception:
            pass

    def action_next_tab(self) -> None:
        """Switch to next tab."""
        try:
            tabbed = self.query_one(TabbedContent)
            if self.get_active_tab() == "events-tab":
                tabbed.active = "users-tab"
            else:
                tabbed.active = "events-tab"
        except Exception:
            pass

    @work(exclusive=True)
    async def load_data_async(self) -> None:
        """Load data in a background worker to avoid blocking UI."""
        self.query_one("#status-bar", Static).update("Loading...")

        try:
            async_session_factory = get_db_connection()
            if not async_session_factory:
                self.db_error = "Database not configured. Run with: doppler run --config dev -- uv run python scripts/manage_events.py"
                self.query_one("#status-bar", Static).update(f"ERROR: {self.db_error}")
                return

            from podium.db.postgres import Event, User

            async with async_session_factory() as session:
                # Load events - explicitly select only the columns we need to avoid lazy loading issues
                result = await session.execute(select(Event))
                db_events = result.scalars().all()

                self.events = [
                    EventData(
                        id=e.id,
                        name=e.name or "",
                        slug=e.slug or "",
                        description=e.description or "",
                        feature_flags_csv=e.feature_flags_csv or "",
                        votable=bool(e.votable),
                        leaderboard_enabled=bool(e.leaderboard_enabled),
                        demo_links_optional=bool(e.demo_links_optional),
                        owner_id=e.owner_id,
                    )
                    for e in db_events
                ]

                # Load users
                result = await session.execute(select(User))
                db_users = result.scalars().all()

                self.users = [
                    UserData(
                        id=u.id,
                        email=u.email or "",
                        display_name=u.display_name or "",
                        first_name=u.first_name or "",
                        last_name=u.last_name or "",
                    )
                    for u in db_users
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
            traceback.print_exc()

    def refresh_events_table(self) -> None:
        try:
            table = self.query_one("#events-table", DataTable)
            table.clear(columns=True)
            table.add_columns("Name", "Slug", "Feature Flags", "V", "L", "Owner")
            table.cursor_type = "row"

            filter_lower = self.filter_text.lower()
            for event in self.events:
                if filter_lower and not any([
                    filter_lower in event.name.lower(),
                    filter_lower in event.slug.lower(),
                    filter_lower in event.feature_flags_csv.lower(),
                ]):
                    continue

                owner = next((u for u in self.users if u.id == event.owner_id), None)
                owner_str = owner.email if owner else str(event.owner_id)[:8]

                table.add_row(
                    event.name[:30],
                    event.slug[:25],
                    event.feature_flags_csv,
                    "✓" if event.votable else "",
                    "✓" if event.leaderboard_enabled else "",
                    owner_str[:25],
                    key=str(event.id),
                )
        except Exception as e:
            self.notify(f"Error refreshing table: {e}", severity="error")

    def refresh_users_table(self) -> None:
        try:
            table = self.query_one("#users-table", DataTable)
            table.clear(columns=True)
            table.add_columns("Email", "Name", "ID")
            table.cursor_type = "row"

            user_filter = ""
            try:
                user_filter = self.query_one("#user-filter-input", Input).value.lower()
            except Exception:
                pass

            for user in self.users:
                if user_filter and not any([
                    user_filter in user.email.lower(),
                    user_filter in user.display_name.lower(),
                    user_filter in user.first_name.lower(),
                ]):
                    continue

                name = user.display_name or f"{user.first_name} {user.last_name}".strip()
                table.add_row(
                    user.email[:35],
                    name[:25],
                    str(user.id),
                    key=str(user.id),
                )
        except Exception as e:
            self.notify(f"Error refreshing users table: {e}", severity="error")

    @on(Input.Changed, "#filter-input")
    def on_filter_changed(self, event: Input.Changed) -> None:
        self.filter_text = event.value
        self.refresh_events_table()

    @on(Input.Changed, "#user-filter-input")
    def on_user_filter_changed(self, event: Input.Changed) -> None:
        self.refresh_users_table()

    @on(Button.Pressed, "#btn-refresh")
    def action_refresh(self) -> None:
        self.load_data_async()
        self.notify("Refreshing...")

    def get_selected_event(self) -> EventData | None:
        """Get the currently selected event from the table."""
        try:
            table = self.query_one("#events-table", DataTable)
            if table.row_count == 0:
                return None

            # Get the row key at cursor position
            row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
            if row_key is None:
                return None

            event_id = str(row_key.value)
            return next((e for e in self.events if str(e.id) == event_id), None)
        except Exception as e:
            self.notify(f"Error getting selection: {e}", severity="error")
            return None

    def get_selected_user(self) -> UserData | None:
        """Get the currently selected user from the table."""
        try:
            table = self.query_one("#users-table", DataTable)
            if table.row_count == 0:
                return None

            row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
            if row_key is None:
                return None

            user_id = str(row_key.value)
            return next((u for u in self.users if str(u.id) == user_id), None)
        except Exception as e:
            self.notify(f"Error getting selection: {e}", severity="error")
            return None

    def action_new_item(self) -> None:
        """New item based on which tab is active."""
        if self.get_active_tab() == "users-tab":
            self.notify("Users sign up themselves - cannot create here", severity="warning")
        else:
            self.do_new_event()

    @on(Button.Pressed, "#btn-new")
    def do_new_event(self) -> None:
        if self.db_error:
            self.notify("Database not connected", severity="error")
            return
        self.push_screen(CreateEventScreen(self.users), self.on_event_created)

    def on_event_created(self, event: EventData | None) -> None:
        if event:
            self.notify(f"Created: {event.name}")
            self.load_data_async()

    def action_edit_item(self) -> None:
        """Edit item based on which tab is active."""
        if self.get_active_tab() == "users-tab":
            self.notify("User editing not supported in this TUI", severity="warning")
        else:
            self.do_edit_event()

    @on(Button.Pressed, "#btn-edit")
    def do_edit_event(self) -> None:
        if self.db_error:
            self.notify("Database not connected", severity="error")
            return

        event = self.get_selected_event()
        if not event:
            self.notify("Select an event first", severity="warning")
            return

        self.push_screen(EditEventScreen(event), self.on_event_edited)

    def on_event_edited(self, saved: bool) -> None:
        if saved:
            self.notify("Event updated")
            self.load_data_async()

    def action_manage_attendees(self) -> None:
        """Open attendees manager for selected event."""
        if self.get_active_tab() != "events-tab":
            return
        self.do_manage_attendees()

    @on(Button.Pressed, "#btn-attendees")
    def do_manage_attendees(self) -> None:
        if self.db_error:
            self.notify("Database not connected", severity="error")
            return

        event = self.get_selected_event()
        if not event:
            self.notify("Select an event first", severity="warning")
            return

        self.push_screen(ManageAttendeesScreen(event, self.users), self.on_attendees_closed)

    def on_attendees_closed(self, _: bool) -> None:
        pass

    def get_active_tab(self) -> str:
        """Get the ID of the currently active tab."""
        try:
            tabbed = self.query_one(TabbedContent)
            return tabbed.active or "events-tab"
        except Exception:
            return "events-tab"

    def action_delete_item(self) -> None:
        """Delete based on which tab is active."""
        if self.get_active_tab() == "users-tab":
            self.on_delete_user()
        else:
            self.do_delete_event()

    @on(Button.Pressed, "#btn-delete")
    def do_delete_event(self) -> None:
        if self.db_error:
            self.notify("Database not connected", severity="error")
            return

        event = self.get_selected_event()
        if not event:
            self.notify("Select an event first", severity="warning")
            return

        self.push_screen(
            ConfirmDialog(f"Delete '{event.name}'?"),
            lambda confirmed: self.do_delete(event, confirmed)
        )

    @work(exclusive=True)
    async def do_delete(self, event: EventData, confirmed: bool) -> None:
        if not confirmed:
            return

        try:
            async_session_factory = get_db_connection()
            if not async_session_factory:
                self.notify("Database not configured", severity="error")
                return

            from podium.db.postgres import Event

            async with async_session_factory() as session:
                db_event = await session.get(Event, event.id)
                if db_event:
                    await session.delete(db_event)
                    await session.commit()

            self.notify(f"Deleted: {event.name}")
            self.load_data_async()
        except Exception as e:
            self.notify(f"Error deleting: {e}", severity="error")
            traceback.print_exc()

    @on(Button.Pressed, "#btn-delete-user")
    def on_delete_user(self) -> None:
        if self.db_error:
            self.notify("Database not connected", severity="error")
            return

        user = self.get_selected_user()
        if not user:
            self.notify("Select a user first", severity="warning")
            return

        self.push_screen(
            ConfirmDialog(f"Delete user '{user.email}'?\nThis will also delete their events, projects, and votes."),
            lambda confirmed: self.do_delete_user(user, confirmed)
        )

    @work(exclusive=True)
    async def do_delete_user(self, user: UserData, confirmed: bool) -> None:
        if not confirmed:
            return

        try:
            async_session_factory = get_db_connection()
            if not async_session_factory:
                self.notify("Database not configured", severity="error")
                return

            from podium.db.postgres import User

            async with async_session_factory() as session:
                db_user = await session.get(User, user.id)
                if db_user:
                    await session.delete(db_user)
                    await session.commit()

            self.notify(f"Deleted user: {user.email}")
            self.load_data_async()
        except Exception as e:
            self.notify(f"Error deleting user: {e}", severity="error")
            traceback.print_exc()


def main() -> None:
    try:
        app = EventManagerApp()
        app.run()
    except Exception as e:
        print(f"Fatal error: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
