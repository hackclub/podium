/**
 * Event Features Registry
 *
 * Central registry for all event-specific features.
 * To add a new event feature:
 * 1. Create a directory under event-features/ with your feature files
 * 2. Implement the EventFeature interface
 * 3. Import and register it here
 */

import type { EventFeature } from "./types";
import { daydreamFeature } from "./daydream";

/**
 * Map of feature flag -> feature definition
 */
const featuresMap = new Map<string, EventFeature>([
  [daydreamFeature.featureFlag, daydreamFeature],
  // Add more event features here as needed
  // [myEventFeature.featureFlag, myEventFeature],
]);

/**
 * Get an event feature by its feature flag
 */
export function getEventFeature(featureFlag: string): EventFeature | undefined {
  return featuresMap.get(featureFlag);
}

/**
 * Get all active features for an event based on its feature flags
 */
export function getActiveFeatures(
  featureFlags: string[] | undefined,
): EventFeature[] {
  if (!featureFlags || featureFlags.length === 0) {
    return [];
  }

  return featureFlags
    .map((flag) => featuresMap.get(flag))
    .filter((feature): feature is EventFeature => feature !== undefined);
}

/**
 * Check if an event has a specific feature
 */
export function hasFeature(
  featureFlags: string[] | undefined,
  featureFlag: string,
): boolean {
  return featureFlags?.includes(featureFlag) || false;
}
