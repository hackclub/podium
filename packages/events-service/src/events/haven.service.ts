import {
  Inject,
  Injectable,
  HttpException,
  HttpStatus,
  ForbiddenException,
  Logger,
} from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { eq, inArray } from 'drizzle-orm';
import type Redis from 'ioredis';
import {
  DRIZZLE_RW,
  DRIZZLE_RO,
  REDIS,
  type Database,
  type User,
  events,
  projects,
  getFeatureFlagsList,
} from '@podium/shared';
import { EventsService, type AttendeeUserData } from './events.service';

// Hack Club Haven keeps its events and signups in Airtable ("YSWS - Haven").
// The dev base is a sandbox copy of production, so table and field IDs are the
// same in both; HAVEN_AIRTABLE_BASE_ID picks which one Podium reads.
const TABLES = {
  events: 'tbl0BQWphHe0gWEIp',
  attendees: 'tblFV1bwpg8vheHHv',
  users: 'tbldXPRdqNRedSOqC',
};

const EVENT = {
  name: 'fldedrTuI1qpSYRE5', // Name, e.g. "Perth"
  status: 'fldP2oeMSijEs3FnR', // Status: Active / Cancelled / On Hold
  format: 'flduc7pPqwujzncxG', // Format: 12-hour / 2-day
  city: 'fldpiLDaR711ywBdq', // City / Region
  attendSlug: 'fld157rMSeJlOIrBR', // Attend Slug, e.g. "haven-perth"
  poc: 'fldgp52NV9DMuXNYX', // POC → Users
  em: 'fldRV0OjedPnLkOby', // EM → Users
  attendees: 'fldHON24yCR1WDkyy', // Attendees → Attendees
  isTest: 'fldmTi25SXVwloyCo', // _Is Test
  workspaceEmail: 'fldBvvlCxogbDMQW9', // _Google Workspace Email, e.g. "perth@haven.hackclub.com"
};

const ATTENDEE = {
  user: 'fld5vodJW3bF8hAwc', // User → Users
  role: 'fld9cd0Ev0s5Xfr9a', // Role: Participant / Organizer / Volunteer
  softDeleted: 'fldMSecqitSMZakQF', // Soft Deleted
  withdrawn: 'fldY7djU4Hv8vyYF9', // !Withdrawn
};

const USER = {
  email: 'fldprtCigX6225wlO',
  firstName: 'fldngRQYSNsbpgUVU',
  lastName: 'fld8bNT3LnqgSBkZb',
  displayName: 'fldQOLScEtYefk2fh',
  phone: 'fldaJ8kopVfacvSzl',
  street1: 'fld5yxGcEBH3vadP7',
  street2: 'fldJKtuOPplp7bgRK',
  city: 'fld1vFfedQd8FP4IP',
  state: 'fldZq8ZlCl0AZ03PP',
  zip: 'fldWMsOjPCIG6Az3m',
  country: 'fldYAXUvw9n5DhRHi',
  birthday: 'fldVEfvE2TfzVmKGi',
};

const SUBMISSION = {
  email: 'fld7e9MNSd0DflwNz', // Email
  podiumProjectId: 'fldu47IuoGFy9Aq6T', // Podium Project ID
};

/** Feature flags every imported Haven event gets. */
const HAVEN_FLAGS = 'haven,roster-only';

/** Field Podium merges submissions on, together with Email. */
const PODIUM_PROJECT_ID_FIELD = 'Podium Project ID';

/** Checkbox Podium sets on submissions whose person left the project, or whose project was deleted. */
const REMOVED_FIELD = '!Removed from Podium';

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

// Airtable allows 5 requests/second per base, shared with everything else
// that talks to the Haven base, and answers a burst over it with 429s for the
// next 30 seconds. Stay at 4/second across every events-service pod.
const AIRTABLE_MIN_INTERVAL_MS = 250;

/**
 * Atomically book the next free request slot on a base and return how many ms
 * the caller must wait for it. Uses Redis's clock so pods with skewed clocks
 * still space their requests correctly.
 */
const RESERVE_SLOT_LUA = `
local key = KEYS[1]
local interval = tonumber(ARGV[1])
local t = redis.call('TIME')
local now = tonumber(t[1]) * 1000 + math.floor(tonumber(t[2]) / 1000)
local slot = math.max(now, tonumber(redis.call('GET', key) or 0))
redis.call('SET', key, slot + interval, 'PX', slot + interval - now + 1000)
return slot - now
`;

// Formula length stays well under Airtable's limit at this many record IDs.
const RECORD_ID_BATCH = 100;

type AirtableRecord = { id: string; fields: Record<string, unknown> };

type HavenEvent = {
  recordId: string;
  name: string;
  status: string;
  format: string;
  city: string;
  slug: string;
  /** Another Haven event has the same Attend Slug; neither can be synced until it's fixed. */
  duplicateSlug: boolean;
  workspaceEmail: string;
  pocUserIds: string[];
  emUserIds: string[];
  attendeeIds: string[];
};

const str = (v: unknown) => (typeof v === 'string' ? v.trim() : '');
const ids = (v: unknown) => (Array.isArray(v) ? v.filter((x): x is string => typeof x === 'string') : []);
const selectName = (v: unknown) =>
  typeof v === 'string' ? v : str((v as { name?: unknown } | null)?.name);

@Injectable()
export class HavenService {
  private readonly logger = new Logger(HavenService.name);
  private readonly airtableToken: string;
  private readonly airtableBaseId: string;
  private readonly submissionsTableId: string;

  /** Earliest time the next Airtable request may start, used only while Redis is unreachable. */
  private nextAirtableSlot = 0;

  constructor(
    @Inject(DRIZZLE_RW) private readonly dbRw: Database,
    @Inject(DRIZZLE_RO) private readonly dbRo: Database,
    @Inject(REDIS) private readonly redis: Redis,
    private readonly config: ConfigService,
    private readonly eventsService: EventsService,
  ) {
    this.airtableToken = config.get<string>('HAVEN_AIRTABLE_TOKEN', '')!;
    this.airtableBaseId = config.get<string>('HAVEN_AIRTABLE_BASE_ID', '')!;
    this.submissionsTableId = config.get<string>('HAVEN_AIRTABLE_SUBMISSIONS_TABLE_ID', '')!;
  }

  // ── Guards ─────────────────────────────────────────────────────────

  private assertConfigured() {
    if (!this.airtableToken || !this.airtableBaseId) {
      throw new HttpException(
        'Haven Airtable is not configured (HAVEN_AIRTABLE_TOKEN, HAVEN_AIRTABLE_BASE_ID)',
        HttpStatus.INTERNAL_SERVER_ERROR,
      );
    }
  }

  private assertSuperadmin(user: User) {
    if (!user.is_superadmin) {
      throw new ForbiddenException('Superadmin access required');
    }
  }

  async isHavenEvent(eventId: string): Promise<boolean> {
    const event = await this.dbRo.query.events.findFirst({
      where: eq(events.id, eventId),
      columns: { feature_flags_csv: true },
    });
    return !!event && getFeatureFlagsList(event).includes('haven');
  }

  // ── Airtable client ────────────────────────────────────────────────

  /**
   * Book the next request slot on the Haven base and return the wait in ms.
   * The slot lives in Redis so all pods share one budget; if Redis is down,
   * fall back to a per-process slot rather than failing the sync.
   */
  private async reserveAirtableSlot(): Promise<number> {
    try {
      return (await this.redis.eval(
        RESERVE_SLOT_LUA,
        1,
        `airtable:next-slot:${this.airtableBaseId}`,
        AIRTABLE_MIN_INTERVAL_MS.toString(),
      )) as number;
    } catch (err) {
      this.logger.warn(`Airtable slot reservation failed, using local slot: ${err}`);
      // Reserve synchronously so concurrent callers queue up behind each other.
      const now = Date.now();
      const slot = Math.max(now, this.nextAirtableSlot);
      this.nextAirtableSlot = slot + AIRTABLE_MIN_INTERVAL_MS;
      return slot - now;
    }
  }

  private async airtableFetch(path: string, init: RequestInit = {}) {
    const wait = await this.reserveAirtableSlot();
    if (wait > 0) {
      await new Promise((resolve) => setTimeout(resolve, wait));
    }

    const res = await fetch(`https://api.airtable.com/v0/${this.airtableBaseId}${path}`, {
      ...init,
      headers: {
        Authorization: `Bearer ${this.airtableToken}`,
        'Content-Type': 'application/json',
        ...((init.headers as Record<string, string>) || {}),
      },
    });
    if (!res.ok) {
      const body = await res.text();
      throw new HttpException(
        `Haven Airtable error: ${res.status} ${body.slice(0, 500)}`,
        HttpStatus.BAD_GATEWAY,
      );
    }
    return res.json();
  }

  /** List every record of a table, optionally filtered, keyed by field ID. */
  private async listRecords(
    tableId: string,
    fields: string[],
    filterByFormula?: string,
  ): Promise<AirtableRecord[]> {
    const records: AirtableRecord[] = [];
    let offset: string | undefined;
    do {
      // POST listRecords keeps long formulas out of the URL.
      const page = await this.airtableFetch(`/${tableId}/listRecords`, {
        method: 'POST',
        body: JSON.stringify({
          fields,
          filterByFormula,
          returnFieldsByFieldId: true,
          pageSize: 100,
          offset,
        }),
      });
      records.push(...page.records);
      offset = page.offset;
    } while (offset);
    return records;
  }

  /** Fetch records by ID, in batches. Missing IDs are skipped. */
  private async getRecordsById(
    tableId: string,
    recordIds: string[],
    fields: string[],
  ): Promise<AirtableRecord[]> {
    const unique = [...new Set(recordIds)];
    const records: AirtableRecord[] = [];
    for (let i = 0; i < unique.length; i += RECORD_ID_BATCH) {
      const batch = unique.slice(i, i + RECORD_ID_BATCH);
      const formula = `OR(${batch.map((id) => `RECORD_ID()='${id}'`).join(',')})`;
      records.push(...(await this.listRecords(tableId, fields, formula)));
    }
    return records;
  }

  // ── Reading Haven ──────────────────────────────────────────────────

  private async fetchHavenEvents(): Promise<HavenEvent[]> {
    const records = await this.listRecords(TABLES.events, Object.values(EVENT));
    const havenEvents = records
      .filter((r) => !r.fields[EVENT.isTest] && str(r.fields[EVENT.attendSlug]))
      .map((r) => ({
        recordId: r.id,
        name: str(r.fields[EVENT.name]),
        status: selectName(r.fields[EVENT.status]),
        format: selectName(r.fields[EVENT.format]),
        city: str(r.fields[EVENT.city]),
        slug: str(r.fields[EVENT.attendSlug]).toLowerCase(),
        duplicateSlug: false,
        workspaceEmail: str(r.fields[EVENT.workspaceEmail]).toLowerCase(),
        pocUserIds: ids(r.fields[EVENT.poc]),
        emUserIds: ids(r.fields[EVENT.em]),
        attendeeIds: ids(r.fields[EVENT.attendees]),
      }));

    // Airtable doesn't enforce unique slugs. Two events on one slug would
    // share a Podium event, so both are refused instead.
    const slugCounts = new Map<string, number>();
    for (const e of havenEvents) slugCounts.set(e.slug, (slugCounts.get(e.slug) ?? 0) + 1);
    for (const e of havenEvents) e.duplicateSlug = slugCounts.get(e.slug)! > 1;
    return havenEvents;
  }

  /**
   * The events' live participants (not soft-deleted or withdrawn) as Airtable
   * User record IDs, by event record ID. Organizers and volunteers are left out:
   * they aren't competing, and POC/EM get admin access separately.
   */
  private async fetchParticipants(havenEvents: HavenEvent[]): Promise<Map<string, string[]>> {
    const eventByAttendee = new Map<string, string>();
    for (const e of havenEvents) {
      for (const id of e.attendeeIds) eventByAttendee.set(id, e.recordId);
    }

    const records = await this.getRecordsById(
      TABLES.attendees,
      [...eventByAttendee.keys()],
      Object.values(ATTENDEE),
    );

    const usersByEvent = new Map<string, string[]>();
    for (const r of records) {
      if (selectName(r.fields[ATTENDEE.role]) !== 'Participant') continue;
      if (r.fields[ATTENDEE.softDeleted] || r.fields[ATTENDEE.withdrawn]) continue;
      const userId = ids(r.fields[ATTENDEE.user])[0];
      const eventId = eventByAttendee.get(r.id);
      if (!userId || !eventId) continue;
      const list = usersByEvent.get(eventId) ?? [];
      list.push(userId);
      usersByEvent.set(eventId, list);
    }
    return usersByEvent;
  }

  /** Haven Users as Podium user data, by Airtable User record ID. Users without an email are skipped. */
  private async fetchUsers(userRecordIds: string[]): Promise<Map<string, AttendeeUserData>> {
    const records = await this.getRecordsById(TABLES.users, userRecordIds, Object.values(USER));
    const byId = new Map<string, AttendeeUserData>();
    for (const r of records) {
      const f = r.fields;
      const email = str(f[USER.email]).toLowerCase();
      if (!email.includes('@')) continue;
      const s = (v: unknown, max: number) => str(v).slice(0, max);
      const firstName = s(f[USER.firstName], 50);
      byId.set(r.id, {
        email,
        display_name: s(f[USER.displayName], 255) || firstName,
        first_name: firstName || email.split('@')[0].slice(0, 50),
        last_name: s(f[USER.lastName], 50),
        phone: s(f[USER.phone], 20),
        street_1: s(f[USER.street1], 255),
        street_2: s(f[USER.street2], 255),
        city: s(f[USER.city], 100),
        state: s(f[USER.state], 100),
        zip_code: s(f[USER.zip], 20),
        country: s(f[USER.country], 100),
        dob: str(f[USER.birthday]) || null,
      });
    }
    return byId;
  }

  // ── Importing ──────────────────────────────────────────────────────

  /**
   * Create or update the Podium events for these Haven events and add their
   * participants to the roster. Active events are enabled and their POC/EM
   * become the event's POC/RM; events that are no longer Active are disabled.
   */
  private async syncHavenEvents(havenEvents: HavenEvent[], owner: User) {
    const active = havenEvents.filter((e) => e.status === 'Active');
    const [participantsByEvent, existingEvents] = await Promise.all([
      this.fetchParticipants(active),
      this.dbRw.query.events.findMany({
        where: inArray(events.slug, havenEvents.map((e) => e.slug)),
      }),
    ]);
    const leaderIds = active.flatMap((e) => [...e.pocUserIds.slice(0, 1), ...e.emUserIds.slice(0, 1)]);
    const users = await this.fetchUsers([...participantsByEvent.values()].flat().concat(leaderIds));
    const existingBySlug = new Map(existingEvents.map((e) => [e.slug, e]));

    const results: {
      slug: string;
      name: string;
      event_id?: string;
      created?: boolean;
      disabled?: boolean;
      attendees_added: number;
      error?: string;
    }[] = [];

    for (const he of havenEvents) {
      const name = `Haven ${he.name}`;
      const existing = existingBySlug.get(he.slug);
      try {
        if (he.duplicateSlug) {
          throw new Error(`Attend Slug ${he.slug} is used by more than one Haven event`);
        }
        if (existing && !getFeatureFlagsList(existing).includes('haven')) {
          throw new Error(`Slug ${he.slug} is already used by a non-Haven event`);
        }

        if (he.status !== 'Active') {
          if (existing?.enabled) {
            await this.dbRw.update(events).set({ enabled: false }).where(eq(events.id, existing.id));
          }
          if (existing) {
            results.push({ slug: he.slug, name, event_id: existing.id, disabled: true, attendees_added: 0 });
          }
          continue;
        }

        const leaderId = async (userRecordIds: string[]) => {
          const data = userRecordIds[0] ? users.get(userRecordIds[0]) : undefined;
          return data ? (await this.eventsService.findOrCreateUser(data)).id : null;
        };
        const pocId = await leaderId(he.pocUserIds);
        const rmId = await leaderId(he.emUserIds);
        // The event's shared Google Workspace account is its owner, which gives
        // it the same admin access as the POC and EM.
        const workspaceId = he.workspaceEmail.includes('@')
          ? (
              await this.eventsService.findOrCreateUser({
                email: he.workspaceEmail,
                display_name: `${name} Organizers`.slice(0, 255),
                first_name: 'Haven',
                last_name: he.name.slice(0, 50),
                phone: '',
                street_1: '',
                street_2: '',
                city: '',
                state: '',
                zip_code: '',
                country: '',
                dob: null,
              })
            ).id
          : null;

        let eventId: string;
        if (existing) {
          eventId = existing.id;
          await this.dbRw
            .update(events)
            .set({ owner_id: workspaceId ?? existing.owner_id, poc_id: pocId, rm_id: rmId, enabled: true })
            .where(eq(events.id, eventId));
        } else {
          const [created] = await this.dbRw
            .insert(events)
            .values({
              name,
              slug: he.slug,
              description: [he.format && `${he.format} game jam`, he.city && `in ${he.city}`]
                .filter(Boolean)
                .join(' '),
              feature_flags_csv: HAVEN_FLAGS,
              theme_name: 'haven',
              theme_font: '',
              theme_primary: '',
              theme_selected: '',
              enabled: true,
              owner_id: workspaceId ?? owner.id,
              poc_id: pocId,
              rm_id: rmId,
            })
            .returning();
          eventId = created.id;
        }

        const roster = (participantsByEvent.get(he.recordId) ?? [])
          .map((id) => users.get(id))
          .filter((u): u is AttendeeUserData => !!u);
        const added = await this.eventsService.syncAttendees(eventId, roster);
        results.push({ slug: he.slug, name, event_id: eventId, created: !existing, attendees_added: added });
      } catch (err: any) {
        this.logger.error(`Haven sync failed for ${he.slug}: ${err.message}`);
        results.push({ slug: he.slug, name, attendees_added: 0, error: err.message || 'Unknown error' });
      }
    }

    return results;
  }

  /** Superadmin: create/update every Haven event and sync all rosters. */
  async syncAll(user: User) {
    this.assertSuperadmin(user);
    this.assertConfigured();

    const havenEvents = await this.fetchHavenEvents();
    const results = await this.syncHavenEvents(havenEvents, user);

    const created = results.filter((r) => r.created).length;
    const disabled = results.filter((r) => r.disabled).length;
    const failed = results.filter((r) => r.error).length;
    const added = results.reduce((s, r) => s + r.attendees_added, 0);
    return {
      message:
        `Synced ${results.length - failed} Haven events (${created} new, ${disabled} disabled), ` +
        `${added} attendees added${failed ? `, ${failed} failed` : ''}`,
      results,
    };
  }

  /** Event admins: pull this event's latest roster from Haven. */
  async syncEvent(eventId: string, user: User) {
    this.assertConfigured();

    const event = await this.dbRw.query.events.findFirst({ where: eq(events.id, eventId) });
    if (!event) {
      throw new HttpException('Event not found', HttpStatus.NOT_FOUND);
    }
    if (!getFeatureFlagsList(event).includes('haven')) {
      throw new HttpException('This event is not a Haven event', HttpStatus.BAD_REQUEST);
    }

    const havenEvent = (await this.fetchHavenEvents()).find((e) => e.slug === event.slug);
    if (!havenEvent) {
      throw new HttpException('No matching Haven event found in Airtable', HttpStatus.NOT_FOUND);
    }

    const [result] = await this.syncHavenEvents([havenEvent], user);
    if (!result) {
      throw new HttpException('Haven event is not active', HttpStatus.BAD_REQUEST);
    }
    if (result.error) {
      throw new HttpException(result.error, HttpStatus.BAD_GATEWAY);
    }
    return {
      message: result.disabled
        ? 'Event disabled (no longer active in Haven)'
        : 'Event synced successfully',
      event_id: eventId,
      attendees_synced: result.attendees_added,
      disabled: result.disabled ?? false,
    };
  }

  // ── Exporting submissions ──────────────────────────────────────────

  /**
   * Upsert one YSWS Project Submission per project member, merged on Email +
   * Podium Project ID so re-syncing updates the same rows and never touches
   * submissions from other programs (e.g. Jumpstart) for the same person.
   * Rows for people who have since left a project, or for deleted projects,
   * are marked removed rather than deleted.
   */
  private async exportProjects(eventIds: string[]) {
    if (!this.submissionsTableId) {
      throw new HttpException(
        'HAVEN_AIRTABLE_SUBMISSIONS_TABLE_ID is not configured',
        HttpStatus.INTERNAL_SERVER_ERROR,
      );
    }
    if (eventIds.length === 0) {
      return { message: 'No Haven events to sync', synced: 0, total: 0 };
    }

    const eventProjects = await this.dbRo.query.projects.findMany({
      where: inArray(projects.event_id, eventIds),
      with: {
        owner: true,
        collaborators: { with: { user: true } },
      },
    });

    const records: { fields: Record<string, unknown> }[] = [];
    for (const p of eventProjects) {
      for (const u of [p.owner, ...p.collaborators.map((c) => c.user)]) {
        const fields: Record<string, unknown> = {
          [PODIUM_PROJECT_ID_FIELD]: p.id,
          Type: 'Satellites',
          'Code URL': p.repo || null,
          'Playable URL': p.demo || null,
          'First Name': u.first_name,
          'Last Name': u.last_name,
          Email: u.email,
          Description: p.description,
          'Address (Line 1)': u.street_1,
          'Address (Line 2)': u.street_2,
          City: u.city,
          'State / Province': u.state,
          'ZIP / Postal Code': u.zip_code,
          Country: u.country,
          Birthday: u.dob || null,
          'Self-reported Hours Spent': p.hours_spent || null,
          [REMOVED_FIELD]: false,
        };
        if (p.image_url) {
          fields['Screenshot'] = [{ url: p.image_url }];
        }
        records.push({ fields });
      }
    }

    let synced = 0;
    const errors: string[] = [];
    for (let i = 0; i < records.length; i += 10) {
      const batch = records.slice(i, i + 10);
      try {
        // No typecast: a missing select option or field should fail loudly
        // instead of quietly changing the Haven base's schema.
        await this.airtableFetch(`/${this.submissionsTableId}`, {
          method: 'PATCH',
          body: JSON.stringify({
            records: batch,
            performUpsert: { fieldsToMergeOn: ['Email', PODIUM_PROJECT_ID_FIELD] },
          }),
        });
        synced += batch.length;
      } catch (err: any) {
        this.logger.error(`Haven submission batch ${i / 10 + 1} failed: ${err.message}`);
        errors.push(`Batch ${i / 10 + 1}: ${err.message}`);
      }
    }

    let removed = 0;
    try {
      removed = await this.markRemovedSubmissions(
        new Set(eventProjects.map((p) => p.id)),
        new Set(records.map((r) => `${r.fields[PODIUM_PROJECT_ID_FIELD]}:${String(r.fields.Email).toLowerCase()}`)),
      );
    } catch (err: any) {
      this.logger.error(`Marking removed Haven submissions failed: ${err.message}`);
      errors.push(`Marking removed submissions: ${err.message}`);
    }

    return {
      message:
        `Synced ${synced} of ${records.length} submission records to Haven's Airtable` +
        (removed ? `, marked ${removed} removed` : ''),
      synced,
      total: records.length,
      removed,
      errors: errors.length > 0 ? errors : undefined,
    };
  }

  /**
   * Check REMOVED_FIELD on Podium's submission rows that are no longer current:
   * the person left one of the exported projects, or the project was deleted.
   * Rows for projects in events that weren't exported are left alone.
   *
   * @param exportedProjectIds every project of the exported events
   * @param currentKeys "projectId:email" of every row just upserted
   */
  private async markRemovedSubmissions(exportedProjectIds: Set<string>, currentKeys: Set<string>) {
    const rows = await this.listRecords(
      this.submissionsTableId,
      Object.values(SUBMISSION),
      `AND({${PODIUM_PROJECT_ID_FIELD}} != '', NOT({${REMOVED_FIELD}}))`,
    );
    const projectIdOf = (r: AirtableRecord) => str(r.fields[SUBMISSION.podiumProjectId]);

    // Projects outside the exported events only count as removed once deleted.
    const otherIds = [
      ...new Set(rows.map(projectIdOf).filter((id) => !exportedProjectIds.has(id) && UUID_RE.test(id))),
    ];
    const stillExist = new Set<string>();
    for (let i = 0; i < otherIds.length; i += 1000) {
      const found = await this.dbRo
        .select({ id: projects.id })
        .from(projects)
        .where(inArray(projects.id, otherIds.slice(i, i + 1000)));
      for (const p of found) stillExist.add(p.id);
    }

    const stale = rows.filter((r) => {
      const projectId = projectIdOf(r);
      if (exportedProjectIds.has(projectId)) {
        const email = str(r.fields[SUBMISSION.email]).toLowerCase();
        return !currentKeys.has(`${projectId}:${email}`);
      }
      return UUID_RE.test(projectId) && !stillExist.has(projectId);
    });

    for (let i = 0; i < stale.length; i += 10) {
      await this.airtableFetch(`/${this.submissionsTableId}`, {
        method: 'PATCH',
        body: JSON.stringify({
          records: stale.slice(i, i + 10).map((r) => ({ id: r.id, fields: { [REMOVED_FIELD]: true } })),
        }),
      });
    }
    return stale.length;
  }

  /** Superadmin: export projects from every Haven event whose voting is closed. */
  async exportAllClosed(user: User) {
    this.assertSuperadmin(user);
    this.assertConfigured();
    const all = await this.dbRo.query.events.findMany();
    const closed = all.filter((e) => getFeatureFlagsList(e).includes('haven') && e.voting_closed);
    return this.exportProjects(closed.map((e) => e.id));
  }

  /** Superadmin: export one Haven event's projects, whatever its stage. */
  async exportEvent(eventId: string, user: User) {
    this.assertSuperadmin(user);
    this.assertConfigured();
    return this.exportProjects([eventId]);
  }
}
