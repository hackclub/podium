// https://svelte.dev/docs/kit/load#Layout-data
import { error, redirect } from "@sveltejs/kit";
import type { PageLoad } from "./$types";
import { user } from "$lib/user.svelte";
import { client, EventsService, ProjectsService, UsersService } from "$lib/client/sdk.gen";
import type { Event, PrivateProject, UserEvents, UserPrivate } from "$lib/client/types.gen";

export const load: PageLoad = async ({ params, fetch, depends }) => {
  let userData: UserPrivate = {} as UserPrivate;
  let projects: PrivateProject[] = [] as PrivateProject[];
  client.setConfig({ fetch });

  if (!user.isAuthenticated) {
    throw error(401, "Unauthorized, try logging in first");
  }

  {
    const {
      data,
      response,
      error: err,
    } = await UsersService.getCurrentUserUsersCurrentGet({
      throwOnError: false,
    });
    if (err || !data) {
      console.error(err, response);
      throw error(response.status, JSON.stringify(err));
    }
    userData = data;
  }

  {
    const {
      data: data,
      response: response,
      error: err,
    } = await ProjectsService.getProjectsProjectsMineGet({
      throwOnError: false,
    });
    if (err || !data) {
      console.error(err, response);
      throw error(response.status, JSON.stringify(err));
    }
    projects = data;
  }

  return {
    userData,
    projects,
  };
};
