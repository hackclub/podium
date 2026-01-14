// https://svelte.dev/docs/kit/load#Layout-data
import { error, redirect } from "@sveltejs/kit";
import type { PageLoad } from "./$types";
import { getAuthenticatedUser } from "$lib/user.svelte";
import { client, EventsService, ProjectsService } from "$lib/client/sdk.gen";
import type { EventPublic, ProjectPrivate, UserEvents } from "$lib/client/types.gen";

export const load: PageLoad = async ({ params, fetch, depends }) => {
  // depends("events:events")
  // depends("projects:mine")

  client.setConfig({ fetch });
  if (!getAuthenticatedUser().access_token) {
    throw error(401, "Unauthorized, try logging in first");
  }

  const {
    data: events,
    error: eventsError,
    response: eventsResponse,
  } = await EventsService.getAttendingEventsEventsGet({
    throwOnError: false,
  });
  if (eventsError || !events) {
    console.error(eventsError, eventsResponse);
    throw error(eventsResponse.status, JSON.stringify(eventsError));
  }

  const {
    data: projects,
    error: projectsError,
    response: projectsResponse,
  } = await ProjectsService.getProjectsProjectsMineGet({
    throwOnError: false,
  });
  if (projectsError || !projects) {
    console.error(projectsError, projectsResponse);
    throw error(projectsResponse.status, JSON.stringify(projectsError));
  }

  return {
    events: events?.attending_events ?? [],
    projects: projects ?? [],
  };
};
