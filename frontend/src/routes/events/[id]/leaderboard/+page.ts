import { error } from "@sveltejs/kit";
import type { PageLoad } from "./$types";
import { client, EventsService } from "$lib/client/sdk.gen";
import type { Project } from "$lib/client/types.gen";

export const load: PageLoad = async ({ params, fetch }) => {
  client.setConfig({ fetch });
  const { id } = params;

  const { data, error: err, response } =
    await EventsService.getLeaderboardEventsEventIdLeaderboardGet({
      path: {
        event_id: id,
      },
      throwOnError: false,
    });
    if (err) {
      console.error(err, response);
      throw error(500, "Failed to load rankings");
    }
  return {
    // If this isn't a list of projects, return an empty list
    // ?. is used to check if projectsResp.data is null/undefined
    projects: (data as Project[]) ?? [],
  };
};
