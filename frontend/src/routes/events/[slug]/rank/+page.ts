import { error } from "@sveltejs/kit";
import type { PageLoad } from "./$types";
import { client, EventsService } from "$lib/client/sdk.gen";
import { getAuthenticatedUser } from "$lib/user.svelte";
import * as Sentry from "@sentry/browser";

export const load: PageLoad = async ({ params, fetch, parent }) => {
  client.setConfig({ fetch });
  const { event } = await parent();
  try {
    const projects =
      await EventsService.getEventProjectsEventsEventIdProjectsGet({
        path: {
          event_id: event.id,
        },
        throwOnError: true,
      });
    if (!projects.data) {
      throw error(404, "No projects found");
    }
    let toSelect = projects.data.length >= 20 ? 3 : 2;

    // Check if user already voted
    // console.debug("Project IDs loaded:", projects.data.map((project) => project.id));
    // console.debug("User votes:", getAuthenticatedUser().user.votes);
    const userVotesInEvent = (getAuthenticatedUser().user.votes || []).filter(
      (vote) => {
        // A project was voted for if project.votes contains the vote ID.
        return projects.data.some((project) => {
          return (project.votes ?? []).includes(vote);
        });
      },
    ).length;
    if (userVotesInEvent > toSelect) {
      Sentry.captureMessage(
        `User has more votes (${userVotesInEvent}) than allowed (${toSelect}) for event ${event.id}`,
      );
    }

    console.debug(
      `User has ${userVotesInEvent} votes in event ${event.id}, can select ${toSelect} more projects`,
    );
    const alreadyVoted = userVotesInEvent >= toSelect;
    if (alreadyVoted) {
      toSelect = 0;
    }
    toSelect = toSelect - userVotesInEvent;

    return { projects: projects.data, toSelect, alreadyVoted };
  } catch (err) {
    console.error(err);
    throw error(500, "Failed to load projects");
  }
};
