import { error } from "@sveltejs/kit";
import type { PageLoad } from "./$types";
import { getAuthenticatedUser } from "$lib/user.svelte";

export const load: PageLoad = async () => {
  // Check if user is authenticated before allowing access to attend page
  if (!getAuthenticatedUser().access_token) {
    throw error(401, "You need to be logged in to join events");
  }

  return {};
};
