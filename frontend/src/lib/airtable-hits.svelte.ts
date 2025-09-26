/**
 * Store to track Airtable API hits per page render
 */

let airtableHits = $state(0);

export function getAirtableHits() {
    return airtableHits;
}

export function addAirtableHits(count: number) {
    airtableHits += count;
}

export function resetAirtableHits() {
    airtableHits = 0;
}
