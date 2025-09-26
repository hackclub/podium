import * as Sentry from "@sentry/sveltekit";
import type { ServerInit } from "@sveltejs/kit";
import { client } from "$lib/client/sdk.gen";
import { getAuthenticatedUser, validateToken } from "$lib/user.svelte";
import { addAirtableHits } from "$lib/airtable-hits.svelte";
// @ts-ignore
import { PUBLIC_API_URL } from "$env/static/public";

// If you don't want to use Session Replay, remove the `Replay` integration,
// `replaysSessionSampleRate` and `replaysOnErrorSampleRate` options.
Sentry.init({
  dsn: "https://489f4a109d07aeadfd13387bcd3197ab@o4508979744210944.ingest.de.sentry.io/4508979747553360",
  replaysSessionSampleRate: 0,
  replaysOnErrorSampleRate: 1,
  integrations: [
    Sentry.replayIntegration({
      maskAllText: false,
    }),
  ],
  sendDefaultPii: false,
});

// Override global fetch to track Airtable API hits transparently
const originalFetch = globalThis.fetch;
globalThis.fetch = async (
  input: RequestInfo | URL,
  init?: RequestInit,
): Promise<Response> => {
  const response = await originalFetch(input, init);

  // Check for Airtable hits header and add to store
  const airtableHits = response.headers.get("X-Airtable-Hits");
  if (airtableHits) {
    const hits = parseInt(airtableHits, 10);
    if (!isNaN(hits)) {
      addAirtableHits(hits);
    }
  }

  return response;
};

client.setConfig({
  baseUrl: PUBLIC_API_URL,
  headers: {
    Authorization: `Bearer ${getAuthenticatedUser().access_token}`,
    "ngrok-skip-browser-warning": "hi",
  },
  // Use throwOnError: false to get proper error handling with response codes
  // When using a conditional to check the err:
  // - For endpoints that return data: use `if (err || !data)` to check both error and null data
  // - For endpoints that don't return data (like POST create/update/delete): use `if (err)` to check only for errors
  throwOnError: false,
});
export const init: ServerInit = async () => {
  if (getAuthenticatedUser().access_token) {
    console.debug("User is already authenticated, checking token");
    await validateToken(getAuthenticatedUser().access_token);
    console.log("Finished auth");
  } else {
    const token = localStorage.getItem("token");
    if (token) {
      console.debug("Token found in localStorage", token);
      await validateToken(token);
      console.log("Finished auth");
    } else {
      console.debug("No token found in localStorage");
    }
    // console.debug('User token: ', user.token);
    // console.debug('Client config: ', client.getConfig());
  }
};
export const handleError = Sentry.handleErrorWithSentry();
