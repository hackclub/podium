// https://svelte.dev/docs/kit/load#Layout-data
import { error, isHttpError, redirect } from "@sveltejs/kit";
import type { LayoutLoad } from "./$types";
import { user } from "$lib/user.svelte";
import { client } from "$lib/client/sdk.gen";
import { EventsService } from "$lib/client/sdk.gen";
import { page } from "$app/state";
import type { Event } from "$lib/client";

let partOfEvent = false;

export const load: LayoutLoad = async ({ params, fetch, url, route }) => {
  client.setConfig({ fetch });

  if (!params.slug) {
    throw error(400, "no slug provided");
  }

  const {
    data: eventId,
    error: errSlug,
    response: responseSlug
  } = await EventsService.getAtIdEventsIdSlugGet({
    path: {
      slug: params.slug,
    },
    throwOnError: false,
  });
  if (errSlug) {
      console.error(errSlug, responseSlug);
      throw error(responseSlug.status, JSON.stringify(errSlug));
  } else {


  const {
    data: event,
    error: errEvent,
    response: responseEvent,
  } = await EventsService.getEventEventsEventIdGet({
    path: {
      event_id: eventId,
    },
    // If the user isn't logged in, just give an empty bearer token. Otherwise, don't set the token since it's already set in the client.
    headers: user.isAuthenticated
      ? {}
      : {
          Authorization: `Bearer SentSinceBearerTokenSeemedToBeNeededForThisToWork`,
        },
    throwOnError: false,
  });
  if (errEvent) {
    console.error(errEvent, responseEvent);
    throw error(responseEvent.status, JSON.stringify(errEvent));
  } else {
    // Check if the user is attending the event
    if (user.isAuthenticated) {
      const {
        data,
        error: err,
        response,
      } = await EventsService.getAttendingEventsEventsGet({
        throwOnError: false,
      });
      if (err) {
        console.error(err, response);
        throw error(response.status, JSON.stringify(err));
      } else {
        partOfEvent =
          data?.attending_events.some((e) => e.id === event.id) || false;
      }
    } else {
      partOfEvent = false;
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
        owned: "attendees" in event,
        partOfEvent,
      },
      title: event.name,
      meta,
    };
  }
}
};
