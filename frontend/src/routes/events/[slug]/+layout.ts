// https://svelte.dev/docs/kit/load#Layout-data
import { error } from "@sveltejs/kit";
import type { LayoutLoad } from "./$types";
import { client } from "$lib/client/sdk.gen";
import { EventsService } from "$lib/client/sdk.gen";
import type { EventPublic, EventPrivate } from "$lib/client";
import { eventSlugAliases } from "$lib/consts";
import { getAuthenticatedUser } from "$lib/user.svelte";

export const load: LayoutLoad = async ({ params, fetch, parent }) => {
  client.setConfig({ fetch });

  if (!params.slug) {
    throw error(400, "no slug provided");
  }

  // Check for alias and replace slug if needed
  const slug =
    (eventSlugAliases as Record<string, string>)[params.slug] || params.slug;

  // Get parent data (user's events) if available
  const { events } = await parent();

  // Check if user has this event in their events
  const attendingEvent = events?.attending_events?.find(
    (e: EventPublic) => e.slug === slug,
  );

  let event: EventPublic | EventPrivate | undefined;
  let partOfEvent = false;
  let owned = false;

  // First, get the event ID from slug
  const {
    data: eventId,
    error: errSlug,
    response: responseSlug,
  } = await EventsService.getAtIdEventsIdSlugGet({
    path: { slug },
    throwOnError: false,
  });

  if (errSlug) {
    console.error(errSlug, responseSlug);
    throw error(responseSlug.status, JSON.stringify(errSlug));
  }

  // Try to get admin view (will succeed if user is owner)
  const currentUser = getAuthenticatedUser();
  if (currentUser.access_token) {
    const {
      data: privateEvent,
      error: adminErr,
    } = await EventsService.getEventAdminEventsAdminEventIdGet({
      path: { event_id: eventId },
      throwOnError: false,
    });

    if (!adminErr && privateEvent) {
      // User is the owner
      event = privateEvent;
      owned = true;
      partOfEvent = attendingEvent !== undefined;
    }
  }

  // If not owner, use attending event or fetch publicly
  if (!owned) {
    if (attendingEvent) {
      event = attendingEvent;
      partOfEvent = true;
    } else {
      const {
        data: publicEvent,
        error: eventErr,
        response: eventResponse,
      } = await EventsService.getEventEndpointEventsEventIdGet({
        path: { event_id: eventId },
        throwOnError: false,
      });

      if (eventErr) {
        console.error(eventErr, eventResponse);
        throw error(eventResponse.status, JSON.stringify(eventErr));
      }

      event = publicEvent;
    }
  }

  if (!event) {
    throw error(404, "Event not found");
  }

  const meta = [
    {
      name: "description",
      content: event.description || "No description provided",
    },
  ];

  return {
    event: {
      ...event,
      owned,
      partOfEvent,
    } as (EventPublic | EventPrivate) & { owned: boolean; partOfEvent: boolean },
    title: event.name,
    meta,
  };
};
