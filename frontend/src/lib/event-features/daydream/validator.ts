/**
 * Daydream Event Validation
 *
 * Validates projects for Daydream events by checking:
 * - Demo URL is a valid itch.io URL
 * - Repo URL is a valid GitHub/Gitee URL
 */

import type { ProjectPublic } from "$lib/client/types.gen";
import type { ValidationResult } from "../types";

// URL validation regexes
export const itchioRegex =
  /^(https?:\/\/)?[a-zA-Z0-9\-_]+\.itch\.io\/[a-zA-Z0-9\-_]+/;
export const githubRegex =
  /^(https?:\/\/)?(github\.com|gitee\.com)\/[a-zA-Z0-9\-_]+\/[a-zA-Z0-9\-_.]+/;

/**
 * Validate a project for Daydream requirements
 */
export function validateDaydreamProject(project: ProjectPublic): ValidationResult {
  const demo = project.demo?.trim() || "";
  const repo = project.repo?.trim() || "";

  // Don't show validation until both URLs are provided
  if (!demo || !repo) {
    return {
      isValid: false,
      message: "Please fill in both demo and repo URLs to validate",
      metadata: {
        swagEligible: false,
      },
    };
  }

  const demoValid = itchioRegex.test(demo);
  const repoValid = githubRegex.test(repo);

  if (demoValid && repoValid) {
    return {
      isValid: true,
      message: "URL checks passed ✅",
      metadata: {
        swagEligible: true,
      },
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
      "repo URL must be a valid GitHub/Gitee URL (format: https://github.com/username/repository)",
    );
  }

  return {
    isValid: false,
    message: `Attendee needs to fix: ${issues.join(", ")}`,
    metadata: {
      swagEligible: false,
    },
  };
}

/**
 * Check if an event has the Daydream feature flag
 */
export function isDaydreamEvent(event: {
  feature_flags_list?: string[];
}): boolean {
  return event.feature_flags_list?.includes("daydream") || false;
}
