/**
 * Flagship Event Configuration
 *
 * Defines which event features should be treated as "flagship" events
 * that get first-class treatment on the homepage and have custom wizards.
 *
 * A flagship event:
 * - Shows a custom wizard on the homepage instead of the generic StartWizard
 * - May have custom project creation forms with specific validation
 * - Gets priority placement in the UI
 */

export interface FlagshipEventConfig {
  /** The feature flag that marks this as a flagship event */
  featureFlag: string;

  /** Display name for the event */
  displayName: string;

  /** Whether this flagship event is currently active */
  active: boolean;

  /** Optional: Custom welcome message for the wizard */
  welcomeMessage?: string;
}

/**
 * List of flagship events. Set `active: true` for events that should
 * appear on the homepage. Only one should be active at a time.
 */
export const flagshipEvents: FlagshipEventConfig[] = [
  {
    featureFlag: "daydream",
    displayName: "Daydream",
    active: true, // Set to true when Daydream is active
    welcomeMessage: "Here's where you can submit your project for",
  },
  // Add future flagship events here:
  // {
  //   featureFlag: "my-hackathon",
  //   displayName: "My Hackathon",
  //   active: true,
  //   welcomeMessage: "Submit your hack for",
  // },
];

/**
 * Get the currently active flagship event config, if any
 */
export function getActiveFlagshipEvent(): FlagshipEventConfig | undefined {
  return flagshipEvents.find((event) => event.active);
}

/**
 * Check if a given feature flag is a flagship event
 */
export function isFlagshipEvent(featureFlag: string): boolean {
  return flagshipEvents.some((event) => event.featureFlag === featureFlag);
}
