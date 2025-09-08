// https://svelte.dev/docs/kit/load#Layout-data
import { error } from "@sveltejs/kit";
import type { LayoutLoad } from "./$types";
import { getAuthenticatedUser } from "$lib/user.svelte";
import { client } from "$lib/client/sdk.gen";
import { EventsService } from "$lib/client/sdk.gen";

export const load: LayoutLoad = async ({ fetch, url }) => {
  client.setConfig({ fetch });
  
  // Check if this is the main events page (not a sub-route)
  const isMainEventsPage = url.pathname === '/events';
  
  // Only load user events if authenticated
  if (getAuthenticatedUser().access_token) {
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
    }
    
    return {
      events: data,
    };
  }
  
  // If unauthenticated and trying to access main events page, throw error
  if (isMainEventsPage) {
    throw error(401, "Unauthorized, try logging in first");
  }
  
  // Return empty events for unauthenticated users on sub-routes
  return {
    events: {
      owned_events: [],
      attending_events: []
    }
  };
};
