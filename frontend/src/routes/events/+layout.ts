// https://svelte.dev/docs/kit/load#Layout-data
import { error } from "@sveltejs/kit";
import type { LayoutLoad } from "./$types";
import { getAuthenticatedUser } from "$lib/user.svelte";
import { client } from "$lib/client/sdk.gen";
import { EventsService } from "$lib/client/sdk.gen";

export const load: LayoutLoad = async ({ fetch }) => {
  client.setConfig({ fetch });

  // Only load attending events if authenticated
  if (getAuthenticatedUser().access_token) {
    const {
      data,
      error: err,
      response,
    } = await EventsService.getAttendingEventsEventsGet({
      throwOnError: false,
    });

    if (err || !data) {
      console.error(err, response);
      throw error(response.status, JSON.stringify(err));
    }

    return {
      events: data,
    };
  }

  // Unauthenticated: no attending events (sub-routes handle public access themselves)
  return {
    events: {
      attending_events: [],
    },
  };
};
