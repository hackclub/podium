ALTER TABLE "events" ADD COLUMN "poc_id" uuid;--> statement-breakpoint
ALTER TABLE "events" ADD COLUMN "rm_id" uuid;--> statement-breakpoint
ALTER TABLE "events" ADD CONSTRAINT "events_poc_id_users_id_fk" FOREIGN KEY ("poc_id") REFERENCES "public"."users"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "events" ADD CONSTRAINT "events_rm_id_users_id_fk" FOREIGN KEY ("rm_id") REFERENCES "public"."users"("id") ON DELETE no action ON UPDATE no action;