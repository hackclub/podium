import { error } from "@sveltejs/kit";
import type { PageLoad } from "./$types";
import { client, EventsService } from "$lib/client/sdk.gen";
import type { Project } from "$lib/client/types.gen";

export const load: PageLoad = async ({ params, fetch }) => {
  client.setConfig({ fetch });
  const { id } = params;
  const {
    data,
    response,
    error: err,
  } = await EventsService.getLeaderboardEventsEventIdLeaderboardGet({
    path: {
      event_id: id,
    },
    // https://github.com/orgs/hey-api/discussions/1655
    throwOnError: false,
  });
  if (err) {
    console.error(err, response);
    throw error(response.status, JSON.stringify(err));
  }
  return {
    // If this isn't a list of projects, return an empty list
    // ?. is used to check if projectsResp.data is null/undefined
    projects: (data as Project[]) ?? [],
  };
};
