import { addAirtableHits } from '$lib/airtable-hits.svelte';

/**
 * Wraps any fetch function to track Airtable API hits
 */
export function createTrackingFetch(originalFetch: typeof fetch): typeof fetch {
  return async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
    const response = await originalFetch(input, init);
    
    // Check for Airtable hits header and add to store
    const airtableHits = response.headers.get('X-Airtable-Hits');
    if (airtableHits) {
      const hits = parseInt(airtableHits, 10);
      if (!isNaN(hits)) {
        addAirtableHits(hits);
      }
    }
    
    return response;
  };
}
