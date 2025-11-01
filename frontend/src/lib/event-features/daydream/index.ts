/**
 * Daydream Event Feature
 *
 * Provides validation and UI for Daydream game jam events.
 */

import type { EventFeature } from "../types";
import { validateDaydreamProject } from "./validator";
import ValidationUI from "./ValidationUI.svelte";

export const daydreamFeature: EventFeature = {
  featureFlag: "daydream",
  name: "Daydream",
  validateProject: validateDaydreamProject,
  ValidationComponent: ValidationUI,
};

// Re-export validator utilities for backward compatibility
export { validateDaydreamProject, isDaydreamEvent, itchioRegex, githubRegex } from "./validator";
