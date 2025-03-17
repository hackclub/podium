import { error } from "@sveltejs/kit";
import type { PageLoad } from "./$types";
import { client, EventsService } from "$lib/client/sdk.gen";
import type { Project } from "$lib/client/types.gen";

export const load: PageLoad = async ({ params, fetch }) => {
  client.setConfig({ fetch });
  const { id } = params;
  try {
    const projectsResp =
      await EventsService.getLeaderboardEventsEventIdLeaderboardGet({
        path: {
          event_id: id,
        },
        throwOnError: true,
      });
    if (!projectsResp?.data) {
      throw error(404, "No leaderboard data found");
    }
    return {
      projects: projectsResp.data as Project[],
    };
  } catch (err) {
    // If it's already an HTTP error, rethrow it
    if (err && typeof err === 'object' && 'status' in err) {
      throw err;
    }
    console.error(err);
    throw error(500, "Failed to load rankings");
  }
};
