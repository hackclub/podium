import { error } from "@sveltejs/kit";
import type { PageLoad } from "./$types";
import { client, EventsService } from "$lib/client/sdk.gen";
import type { ProjectPublic } from "$lib/client/types.gen";

export const load: PageLoad = async ({ params, fetch, parent }) => {
  client.setConfig({ fetch });

  const { event } = await parent();
  const {
    data,
    response,
    error: err,
  } = await EventsService.getEventProjectsEventsEventIdProjectsGet({
    path: {
      event_id: event.id,
    },
    query: {
      leaderboard: true,
    },
    // https://github.com/orgs/hey-api/discussions/1655
    throwOnError: false,
  });
  if (err || !data) {
    console.error(err, response);
    throw error(response.status, JSON.stringify(err));
  }
  return {
    // If this isn't a list of projects, return an empty list
    // ?. is used to check if projectsResp.data is null/undefined
    projects: (data as ProjectPublic[]) ?? [],
  };
};
