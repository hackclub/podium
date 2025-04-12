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

  if (!params.id) {
    throw error(400, "no id provided");
  }

  let event: { data: Event | null } = {
    data: null,
  };

  try {
    event = await EventsService.getEventEventsEventIdGet({
      path: {
        event_id: params.id,
      },
      // If the user isn't logged in, just give an empty bearer token. Otherwise, don't set the token since it's already set in the client.
      headers: user.isAuthenticated
        ? {}
        : {
            Authorization: `Bearer SentSinceBearerTokenSeemedToBeNeededForThisToWork`,
          },
      throwOnError: true,
    });
    if (!event.data) {
      throw error(404, "Event not found");
    }

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
          data?.attending_events.some((e) => e.id === event.data?.id) || false;
      }
    } else {
      partOfEvent = false;
    }

    const meta = [
      {
        name: "description",
        content: event.data.description || "No description provided",
      },
    ];
    return {
      event: {
        ...event.data,
        owned: "attendees" in event,
        partOfEvent,
      },
      title: event.data.name,
      meta,
    };
  } catch (err) {
    console.error(err);
    throw error(500, "Failed to load event");
  }
};
