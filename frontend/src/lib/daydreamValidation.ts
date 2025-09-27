/**
 * URL validation utilities for Daydream events
 * These regex patterns match the validation used in DaydreamCreateProject.svelte
 */

// URL validation regexes (same as in DaydreamCreateProject.svelte)
export const itchioRegex =
  /^(https?:\/\/)?[a-zA-Z0-9\-_]+\.itch\.io\/[a-zA-Z0-9\-_]+/;
export const githubRegex =
  /^(https?:\/\/)?(github\.com|gitee\.com)\/[a-zA-Z0-9\-_]+\/[a-zA-Z0-9\-_.]+/;

export interface URLValidationResult {
  isValid: boolean;
  message: string;
  swagEligible: boolean;
}

/**
 * Validate project URLs for Daydream events
 * @param demoUrl - The demo URL (itch.io)
 * @param repoUrl - The repository URL (GitHub/Gitee)
 * @returns Validation result with status and message
 */
export function validateDaydreamURLs(
  demoUrl: string | null | undefined,
  repoUrl: string | null | undefined,
): URLValidationResult {
  const demo = demoUrl?.trim() || "";
  const repo = repoUrl?.trim() || "";

  const demoValid = !demo || itchioRegex.test(demo);
  const repoValid = !repo || githubRegex.test(repo);

  if (demoValid && repoValid) {
    return {
      isValid: true,
      message: "URL checks passed ✅",
      swagEligible: true,
    };
  }

  const issues = [];
  if (demo && !demoValid) {
    issues.push(
      "demo URL must be a valid itch.io URL (format: https://username.itch.io/gamename)",
    );
  }
  if (repo && !repoValid) {
    issues.push(
      "repo URL must be a valid GitHub URL (format: https://github.com/username/repository)",
    );
  }

  return {
    isValid: false,
    message: `Attendee needs to fix: ${issues.join(", ")}`,
    swagEligible: false,
  };
}

/**
 * Check if an event is a Daydream event
 * @param event - The event object
 * @returns true if the event has the daydream feature flag
 */
export function isDaydreamEvent(event: {
  feature_flags_list?: string[];
}): boolean {
  return event.feature_flags_list?.includes("daydream") || false;
}
