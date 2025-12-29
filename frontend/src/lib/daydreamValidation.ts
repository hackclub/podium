/**
 * @deprecated This file is deprecated. Import from "$lib/event-features/daydream" instead.
 *
 * Backward compatibility exports for Daydream validation utilities.
 * These now use the new event features system.
 */

import {
  itchioRegex as _itchioRegex,
  githubRegex as _githubRegex,
  isDaydreamEvent as _isDaydreamEvent,
  validateDaydreamProject,
} from "$lib/event-features/daydream";
import type { ProjectPublic } from "$lib/client/types.gen";

// Re-export regexes
export const itchioRegex = _itchioRegex;
export const githubRegex = _githubRegex;
export const isDaydreamEvent = _isDaydreamEvent;

/**
 * @deprecated Use validateDaydreamProject from "$lib/event-features/daydream" instead
 */
export interface URLValidationResult {
  isValid: boolean;
  message: string;
  swagEligible: boolean;
}

/**
 * Validate project URLs for Daydream events
 * @deprecated Use the event features system instead
 * @param demoUrl - The demo URL (itch.io)
 * @param repoUrl - The repository URL (GitHub/Gitee)
 * @returns Validation result with status and message
 */
export function validateDaydreamURLs(
  demoUrl: string | null | undefined,
  repoUrl: string | null | undefined,
): URLValidationResult {
  // Create a minimal project object to use the new validator
  const project: Partial<ProjectPublic> = {
    demo: demoUrl || undefined,
    repo: repoUrl || undefined,
  };

  const result = validateDaydreamProject(project as ProjectPublic);

  return {
    isValid: result.isValid,
    message: result.message,
    swagEligible: result.metadata?.swagEligible || false,
  };
}
