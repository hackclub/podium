CREATE TABLE "admin_otps" (
	"email" varchar(255) PRIMARY KEY NOT NULL,
	"code" varchar(6) NOT NULL,
	"expires_at" bigint NOT NULL
);

CREATE TABLE "event_attendees" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"event_id" uuid NOT NULL,
	"user_id" uuid NOT NULL,
	CONSTRAINT "event_attendees_event_id_user_id_unique" UNIQUE("event_id","user_id")
);

CREATE TABLE "events" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"name" varchar(255) NOT NULL,
	"slug" varchar(50) NOT NULL,
	"description" text DEFAULT '' NOT NULL,
	"enabled" boolean DEFAULT false NOT NULL,
	"votable" boolean DEFAULT false NOT NULL,
	"voting_closed" boolean DEFAULT false NOT NULL,
	"leaderboard_enabled" boolean DEFAULT false NOT NULL,
	"demo_links_optional" boolean DEFAULT false NOT NULL,
	"ysws_checks_enabled" boolean DEFAULT false NOT NULL,
	"itch_verification_disabled" boolean DEFAULT false NOT NULL,
	"feature_flags_csv" varchar(500) DEFAULT '' NOT NULL,
	"theme_name" varchar(50) DEFAULT 'campfire' NOT NULL,
	"theme_background" text DEFAULT '' NOT NULL,
	"theme_font" varchar(100) DEFAULT '"Ember& Fire", sans-serif' NOT NULL,
	"theme_primary" varchar(20) DEFAULT '#49B6F3' NOT NULL,
	"theme_selected" varchar(20) DEFAULT '#F59E0B' NOT NULL,
	"owner_id" uuid NOT NULL,
	"poc_id" uuid,
	"rm_id" uuid,
	CONSTRAINT "events_slug_unique" UNIQUE("slug")
);

CREATE TABLE "project_collaborators" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"project_id" uuid NOT NULL,
	"user_id" uuid NOT NULL,
	CONSTRAINT "project_collaborators_project_id_user_id_unique" UNIQUE("project_id","user_id")
);

CREATE TABLE "projects" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"name" varchar(255) NOT NULL,
	"repo" text DEFAULT '' NOT NULL,
	"image_url" text DEFAULT '' NOT NULL,
	"demo" text DEFAULT '' NOT NULL,
	"description" text DEFAULT '' NOT NULL,
	"join_code" varchar(20) NOT NULL,
	"hours_spent" integer DEFAULT 0 NOT NULL,
	"manual_points" integer DEFAULT 0 NOT NULL,
	"owner_id" uuid NOT NULL,
	"event_id" uuid NOT NULL,
	CONSTRAINT "projects_join_code_unique" UNIQUE("join_code")
);

CREATE TABLE "referrals" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"content" text DEFAULT '' NOT NULL,
	"user_id" uuid NOT NULL,
	"event_id" uuid NOT NULL
);

CREATE TABLE "users" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"email" varchar(255) NOT NULL,
	"display_name" varchar(255) DEFAULT '' NOT NULL,
	"first_name" varchar(50) NOT NULL,
	"last_name" varchar(50) DEFAULT '' NOT NULL,
	"is_admin" boolean DEFAULT false NOT NULL,
	"is_superadmin" boolean DEFAULT false NOT NULL,
	"phone" varchar(20) DEFAULT '' NOT NULL,
	"street_1" varchar(255) DEFAULT '' NOT NULL,
	"street_2" varchar(255) DEFAULT '' NOT NULL,
	"city" varchar(100) DEFAULT '' NOT NULL,
	"state" varchar(100) DEFAULT '' NOT NULL,
	"zip_code" varchar(20) DEFAULT '' NOT NULL,
	"country" varchar(100) DEFAULT '' NOT NULL,
	"dob" date,
	CONSTRAINT "users_email_unique" UNIQUE("email")
);

CREATE TABLE "votes" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"voter_id" uuid NOT NULL,
	"project_id" uuid NOT NULL,
	"event_id" uuid NOT NULL,
	CONSTRAINT "votes_voter_id_project_id_unique" UNIQUE("voter_id","project_id")
);

ALTER TABLE "event_attendees" ADD CONSTRAINT "event_attendees_event_id_events_id_fk" FOREIGN KEY ("event_id") REFERENCES "public"."events"("id") ON DELETE no action ON UPDATE no action;
ALTER TABLE "event_attendees" ADD CONSTRAINT "event_attendees_user_id_users_id_fk" FOREIGN KEY ("user_id") REFERENCES "public"."users"("id") ON DELETE no action ON UPDATE no action;
ALTER TABLE "events" ADD CONSTRAINT "events_owner_id_users_id_fk" FOREIGN KEY ("owner_id") REFERENCES "public"."users"("id") ON DELETE no action ON UPDATE no action;
ALTER TABLE "events" ADD CONSTRAINT "events_poc_id_users_id_fk" FOREIGN KEY ("poc_id") REFERENCES "public"."users"("id") ON DELETE no action ON UPDATE no action;
ALTER TABLE "events" ADD CONSTRAINT "events_rm_id_users_id_fk" FOREIGN KEY ("rm_id") REFERENCES "public"."users"("id") ON DELETE no action ON UPDATE no action;
ALTER TABLE "project_collaborators" ADD CONSTRAINT "project_collaborators_project_id_projects_id_fk" FOREIGN KEY ("project_id") REFERENCES "public"."projects"("id") ON DELETE no action ON UPDATE no action;
ALTER TABLE "project_collaborators" ADD CONSTRAINT "project_collaborators_user_id_users_id_fk" FOREIGN KEY ("user_id") REFERENCES "public"."users"("id") ON DELETE no action ON UPDATE no action;
ALTER TABLE "projects" ADD CONSTRAINT "projects_owner_id_users_id_fk" FOREIGN KEY ("owner_id") REFERENCES "public"."users"("id") ON DELETE no action ON UPDATE no action;
ALTER TABLE "projects" ADD CONSTRAINT "projects_event_id_events_id_fk" FOREIGN KEY ("event_id") REFERENCES "public"."events"("id") ON DELETE no action ON UPDATE no action;
ALTER TABLE "referrals" ADD CONSTRAINT "referrals_user_id_users_id_fk" FOREIGN KEY ("user_id") REFERENCES "public"."users"("id") ON DELETE no action ON UPDATE no action;
ALTER TABLE "referrals" ADD CONSTRAINT "referrals_event_id_events_id_fk" FOREIGN KEY ("event_id") REFERENCES "public"."events"("id") ON DELETE no action ON UPDATE no action;
ALTER TABLE "votes" ADD CONSTRAINT "votes_voter_id_users_id_fk" FOREIGN KEY ("voter_id") REFERENCES "public"."users"("id") ON DELETE no action ON UPDATE no action;
ALTER TABLE "votes" ADD CONSTRAINT "votes_project_id_projects_id_fk" FOREIGN KEY ("project_id") REFERENCES "public"."projects"("id") ON DELETE no action ON UPDATE no action;
ALTER TABLE "votes" ADD CONSTRAINT "votes_event_id_events_id_fk" FOREIGN KEY ("event_id") REFERENCES "public"."events"("id") ON DELETE no action ON UPDATE no action;
