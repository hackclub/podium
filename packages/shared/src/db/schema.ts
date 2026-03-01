import {
  pgTable,
  uuid,
  varchar,
  text,
  boolean,
  integer,
  bigint,
  date,
  unique,
} from 'drizzle-orm/pg-core';
import { relations } from 'drizzle-orm';

// ── Tables ──────────────────────────────────────────────────────────────

export const users = pgTable('users', {
  id: uuid('id').primaryKey().defaultRandom(),
  email: varchar('email', { length: 255 }).notNull().unique(),
  display_name: varchar('display_name', { length: 255 }).notNull().default(''),
  first_name: varchar('first_name', { length: 50 }).notNull(),
  last_name: varchar('last_name', { length: 50 }).notNull().default(''),
  is_admin: boolean('is_admin').notNull().default(false),
  is_superadmin: boolean('is_superadmin').notNull().default(false),
  phone: varchar('phone', { length: 20 }).notNull().default(''),
  street_1: varchar('street_1', { length: 255 }).notNull().default(''),
  street_2: varchar('street_2', { length: 255 }).notNull().default(''),
  city: varchar('city', { length: 100 }).notNull().default(''),
  state: varchar('state', { length: 100 }).notNull().default(''),
  zip_code: varchar('zip_code', { length: 20 }).notNull().default(''),
  country: varchar('country', { length: 100 }).notNull().default(''),
  dob: date('dob'),
});

export const events = pgTable('events', {
  id: uuid('id').primaryKey().defaultRandom(),
  name: varchar('name', { length: 255 }).notNull(),
  slug: varchar('slug', { length: 50 }).notNull().unique(),
  description: text('description').notNull().default(''),
  enabled: boolean('enabled').notNull().default(false),
  votable: boolean('votable').notNull().default(false),
  voting_closed: boolean('voting_closed').notNull().default(false),
  leaderboard_enabled: boolean('leaderboard_enabled').notNull().default(false),
  demo_links_optional: boolean('demo_links_optional').notNull().default(false),
  ysws_checks_enabled: boolean('ysws_checks_enabled').notNull().default(false),
  itch_verification_disabled: boolean('itch_verification_disabled').notNull().default(false),
  feature_flags_csv: varchar('feature_flags_csv', { length: 500 }).notNull().default(''),
  theme_name: varchar('theme_name', { length: 50 }).notNull().default('campfire'),
  theme_background: text('theme_background').notNull().default(''),
  theme_font: varchar('theme_font', { length: 100 }).notNull().default('"Ember& Fire", sans-serif'),
  theme_primary: varchar('theme_primary', { length: 20 }).notNull().default('#49B6F3'),
  theme_selected: varchar('theme_selected', { length: 20 }).notNull().default('#F59E0B'),
  owner_id: uuid('owner_id').notNull().references(() => users.id),
  poc_id: uuid('poc_id').references(() => users.id),
  rm_id: uuid('rm_id').references(() => users.id),
});

export const projects = pgTable('projects', {
  id: uuid('id').primaryKey().defaultRandom(),
  name: varchar('name', { length: 255 }).notNull(),
  repo: text('repo').notNull().default(''),
  image_url: text('image_url').notNull().default(''),
  demo: text('demo').notNull().default(''),
  description: text('description').notNull().default(''),
  join_code: varchar('join_code', { length: 20 }).notNull().unique(),
  hours_spent: integer('hours_spent').notNull().default(0),
  manual_points: integer('manual_points').notNull().default(0),
  owner_id: uuid('owner_id').notNull().references(() => users.id),
  event_id: uuid('event_id').notNull().references(() => events.id),
});

export const votes = pgTable(
  'votes',
  {
    id: uuid('id').primaryKey().defaultRandom(),
    voter_id: uuid('voter_id').notNull().references(() => users.id),
    project_id: uuid('project_id').notNull().references(() => projects.id),
    event_id: uuid('event_id').notNull().references(() => events.id),
  },
  (t) => [unique().on(t.voter_id, t.project_id)],
);

export const referrals = pgTable('referrals', {
  id: uuid('id').primaryKey().defaultRandom(),
  content: text('content').notNull().default(''),
  user_id: uuid('user_id').notNull().references(() => users.id),
  event_id: uuid('event_id').notNull().references(() => events.id),
});

export const eventAttendees = pgTable(
  'event_attendees',
  {
    id: uuid('id').primaryKey().defaultRandom(),
    event_id: uuid('event_id').notNull().references(() => events.id),
    user_id: uuid('user_id').notNull().references(() => users.id),
  },
  (t) => [unique().on(t.event_id, t.user_id)],
);

export const projectCollaborators = pgTable(
  'project_collaborators',
  {
    id: uuid('id').primaryKey().defaultRandom(),
    project_id: uuid('project_id').notNull().references(() => projects.id),
    user_id: uuid('user_id').notNull().references(() => users.id),
  },
  (t) => [unique().on(t.project_id, t.user_id)],
);

export const adminOtps = pgTable('admin_otps', {
  email: varchar('email', { length: 255 }).primaryKey(),
  code: varchar('code', { length: 6 }).notNull(),
  expires_at: bigint('expires_at', { mode: 'number' }).notNull(),
});

// ── Relations ───────────────────────────────────────────────────────────

export const usersRelations = relations(users, ({ many }) => ({
  owned_events: many(events, { relationName: 'event_owner' }),
  poc_events: many(events, { relationName: 'event_poc' }),
  rm_events: many(events, { relationName: 'event_rm' }),
  owned_projects: many(projects),
  votes: many(votes),
  referrals: many(referrals),
  event_attendees: many(eventAttendees),
  project_collaborators: many(projectCollaborators),
}));

export const eventsRelations = relations(events, ({ one, many }) => ({
  owner: one(users, { fields: [events.owner_id], references: [users.id], relationName: 'event_owner' }),
  poc: one(users, { fields: [events.poc_id], references: [users.id], relationName: 'event_poc' }),
  rm: one(users, { fields: [events.rm_id], references: [users.id], relationName: 'event_rm' }),
  projects: many(projects),
  votes: many(votes),
  referrals: many(referrals),
  attendees: many(eventAttendees),
}));

export const projectsRelations = relations(projects, ({ one, many }) => ({
  owner: one(users, { fields: [projects.owner_id], references: [users.id] }),
  event: one(events, { fields: [projects.event_id], references: [events.id] }),
  votes: many(votes),
  collaborators: many(projectCollaborators),
}));

export const votesRelations = relations(votes, ({ one }) => ({
  voter: one(users, { fields: [votes.voter_id], references: [users.id] }),
  project: one(projects, { fields: [votes.project_id], references: [projects.id] }),
  event: one(events, { fields: [votes.event_id], references: [events.id] }),
}));

export const referralsRelations = relations(referrals, ({ one }) => ({
  user: one(users, { fields: [referrals.user_id], references: [users.id] }),
  event: one(events, { fields: [referrals.event_id], references: [events.id] }),
}));

export const eventAttendeesRelations = relations(eventAttendees, ({ one }) => ({
  event: one(events, { fields: [eventAttendees.event_id], references: [events.id] }),
  user: one(users, { fields: [eventAttendees.user_id], references: [users.id] }),
}));

export const projectCollaboratorsRelations = relations(projectCollaborators, ({ one }) => ({
  project: one(projects, { fields: [projectCollaborators.project_id], references: [projects.id] }),
  user: one(users, { fields: [projectCollaborators.user_id], references: [users.id] }),
}));

// ── Helper functions (replace class getters) ────────────────────────────

export type Event = typeof events.$inferSelect;
export type NewEvent = typeof events.$inferInsert;
export type User = typeof users.$inferSelect;
export type NewUser = typeof users.$inferInsert;
export type Project = typeof projects.$inferSelect;
export type NewProject = typeof projects.$inferInsert;
export type Vote = typeof votes.$inferSelect;
export type NewVote = typeof votes.$inferInsert;
export type Referral = typeof referrals.$inferSelect;
export type EventAttendee = typeof eventAttendees.$inferSelect;
export type ProjectCollaborator = typeof projectCollaborators.$inferSelect;

export function getFeatureFlagsList(event: { feature_flags_csv: string }): string[] {
  if (!event.feature_flags_csv) return [];
  return event.feature_flags_csv
    .split(',')
    .map((f) => f.trim())
    .filter(Boolean);
}

export function getMaxVotesPerUser(): number {
  return 3;
}

export function getPoints(voteCount: number): number {
  return voteCount;
}
