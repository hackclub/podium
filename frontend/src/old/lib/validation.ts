import { client } from "./client/sdk.gen";

/**
 * Regex for itch.io URL validation
 */
export function isValidItchUrl(url: string): boolean {
  const regex = /^(https?:\/\/)?[a-zA-Z0-9\-_]+\.itch\.io\/[a-zA-Z0-9\-_]+/;
  return regex.test(url?.trim() || "");
}

/**
 * Regex for GitHub URL validation
 */
export function isValidGitHubUrl(url: string): boolean {
  const regex =
    /^(https?:\/\/)?(github\.com|gitee\.com)\/[a-zA-Z0-9\-_]+\/[a-zA-Z0-9\-_.]+/;
  return regex.test(url?.trim() || "");
}

export interface ValidationResult {
  valid: boolean;
  message: string;
}

/**
 * Validate a project's demo URL via the backend itch-police validator.
 * Calls POST /projects/validate
 */
export async function validateProject(
  projectId: string,
): Promise<ValidationResult> {
  try {
    const response = await client.post<ValidationResult>({
      url: "/projects/validate",
      query: { project_id: projectId },
    });

    if (response.error || !response.data) {
      return {
        valid: false,
        message: "Validation request failed. Please try again.",
      };
    }

    return {
      valid: response.data.valid,
      message: response.data.message,
    };
  } catch (err) {
    console.error("Validation error:", err);
    return {
      valid: false,
      message: "Validation request failed. Please try again.",
    };
  }
}
