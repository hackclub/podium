import { ProjectsService, type Unified } from "./client";
import { getEventFeature } from "./event-features/registry";
import type { ValidationResult } from "./event-features/types";

/**
 * Poll for completion of a project quality check
 */
export async function pollForCompletion(
  checkId: string,
): Promise<Unified | null> {
  const maxAttempts = 60; // 5 minutes with 5-second intervals

  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    try {
      const { data: checkStatus, error } =
        await ProjectsService.pollProjectCheckProjectsCheckCheckIdGet({
          path: { check_id: checkId },
          throwOnError: false,
        });

      if (error || !checkStatus) {
        console.error("Polling error:", error);
        return null;
      }

      if (checkStatus.status === "completed" && checkStatus.result) {
        return checkStatus.result;
      }

      if (checkStatus.status === "failed") {
        console.error("Check failed:", checkStatus.error);
        return null;
      }

      // Wait 5 seconds before next poll
      await new Promise((resolve) => setTimeout(resolve, 5000));
    } catch (error) {
      console.error("Polling error:", error);
      return null;
    }
  }

  console.error("Check timed out");
  return null;
}

/**
 * Check project quality - uses event validators for flagship events, review-factory otherwise
 */
export async function checkProjectQuality(
  project: any,
  eventFeatureFlag?: string,
): Promise<Unified | ValidationResult | null> {
  // If this is a flagship event with a custom validator, use that instead of review-factory
  if (eventFeatureFlag) {
    const eventFeature = getEventFeature(eventFeatureFlag);
    if (eventFeature?.validateProject) {
      try {
        return await Promise.resolve(eventFeature.validateProject(project));
      } catch (error) {
        console.error("Event validator error:", error);
        return null;
      }
    }
  }

  // Fall back to review-factory for non-flagship events
  try {
    const { data: checkStatus, error } =
      await ProjectsService.startProjectCheckProjectsCheckStartPost({
        body: { ...project },
        throwOnError: false,
      });

    if (error || !checkStatus) {
      console.error("Failed to start check:", error);
      return null;
    }

    if (checkStatus.status === "completed" && checkStatus.result) {
      // Already completed (cached result)
      return checkStatus.result;
    } else {
      // Poll for completion
      return await pollForCompletion(checkStatus.check_id);
    }
  } catch (error) {
    console.error("Error checking project:", error);
    return null;
  }
}
