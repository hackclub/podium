import { ProjectsService, type Result } from "./client";

/**
 * Poll for completion of a project quality check
 */
export async function pollForCompletion(checkId: string): Promise<Result | null> {
  const maxAttempts = 60; // 5 minutes with 5-second intervals
  
  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    try {
      const { data: checkStatus, error } = await ProjectsService.pollProjectCheckProjectsCheckCheckIdGet({
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
      await new Promise(resolve => setTimeout(resolve, 5000));
    } catch (error) {
      console.error("Polling error:", error);
      return null;
    }
  }
  
  console.error("Check timed out");
  return null;
}

/**
 * Check project quality with async polling
 */
export async function checkProjectQuality(project: any): Promise<Result | null> {
  try {
    const { data: checkStatus, error } = await ProjectsService.startProjectCheckProjectsCheckStartPost({
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