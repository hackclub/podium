// https://svelte.dev/docs/kit/load#Layout-data
import { error } from "@sveltejs/kit";
import type { LayoutLoad } from "./$types";
import { client } from "$lib/client/sdk.gen";
import { EventsService } from "$lib/client/sdk.gen";
import type { Event, PrivateEvent } from "$lib/client";
import { eventSlugAliases } from "$lib/consts";

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
  const ownedEvent = events?.owned_events.find((e) => e.slug === slug);
  const attendingEvent = events?.attending_events.find((e) => e.slug === slug);
  
  let event: Event | PrivateEvent;
  let partOfEvent = false;
  let owned = false;

  if (ownedEvent) {
    // User owns this event, use the PrivateEvent
    event = ownedEvent;
    partOfEvent = true;
    owned = true;
  } else if (attendingEvent) {
    // User is attending this event, use the regular Event
    event = attendingEvent;
    partOfEvent = true;
    owned = false;
  } else {
    // User doesn't have this event, fetch it publicly
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

    const {
      data: publicEvent,
      error: eventErr,
      response: eventResponse,
    } = await EventsService.getEventEventsEventIdGet({
      path: { event_id: eventId },
      throwOnError: false,
    });
    
    if (eventErr) {
      console.error(eventErr, eventResponse);
      throw error(eventResponse.status, JSON.stringify(eventErr));
    }
    
    event = publicEvent;
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
    } as (Event | PrivateEvent) & { owned: boolean; partOfEvent: boolean },
    title: event.name,
    meta,
  };
};
