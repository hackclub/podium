import { error } from "@sveltejs/kit";
import type { PageLoad } from "./$types";
import { client, EventsService } from "$lib/client/sdk.gen";

export const load: PageLoad = async ({ params, fetch }) => {
  client.setConfig({ fetch });
  const { id } = params;

  try {
    const projects =
      await EventsService.getEventProjectsEventsEventIdProjectsGet({
        path: {
          event_id: id,
        },
        throwOnError: true,
      });
    if (!projects.data) {
      throw error(404, "No projects found");
    }
    return { projects: projects.data };
  } catch (err) {
    // If it's already an HTTP error, rethrow it
    if (err && typeof err === 'object' && 'status' in err) {
      throw err;
    }
    console.error(err);
    throw error(500, "Failed to load projects");
  }
};
