import type { HTTPValidationError } from "$lib/client/types.gen";
import { toast } from "svelte-sonner";
import { lightTheme, darkTheme, loadingTextOptions } from "$lib/consts";
import { invalidate, invalidateAll } from "$app/navigation";
import { getAuthenticatedUser, validateToken } from "./user.svelte";

type ErrorWithDetail = {
  detail: string;
};

export function handleError(
  error: HTTPValidationError | ErrorWithDetail | Error | unknown,
) {
  // If it's a FastAPI HTTPException, it will have a detail field. Same with validation errors.
  console.error("Error", error);
  if (error && typeof error === "object" && "detail" in error) {
    if (Array.isArray(error?.detail)) {
      // const invalidFields = error.detail.map((e) => e.msg);
      const invalidFields = error.detail.map(
        (e) => `${e.loc.join(".")}: ${e.msg}`,
      );
      toast.error(invalidFields.join(" | "));
    } else if (typeof error?.detail === "string") {
      toast.error(error.detail);
    }
  } else {
    if (error instanceof Error) {
      toast.error(error.message);
    } else {
      toast.error("An error occurred, check the console for more details");
    }
  }
}

export function setSystemTheme() {
  // If the user has set a theme preference, don't override it
  if (localStorage.theme) {
    return;
  }
  if (window.matchMedia("(prefers-color-scheme: dark)").matches) {
    document.documentElement.setAttribute("data-theme", darkTheme);
  } else if (window.matchMedia("(prefers-color-scheme: light)").matches) {
    document.documentElement.setAttribute("data-theme", lightTheme);
  }
}

export function returnLoadingText(): string {
  return loadingTextOptions[
    Math.floor(Math.random() * loadingTextOptions.length)
  ];
}

export async function invalidateEvents() {
  await invalidate((url) => url.pathname.startsWith("/events"));
}
export async function invalidateProjects() {
  await invalidate((url) => url.pathname.startsWith("/projects"));
}

/**
 * Reload the user's data.
 * This does not actually call a load function but rather re-requests user data by checking the token again.
 */
export function invalidateUser(): Promise<void> {
  return validateToken(getAuthenticatedUser().access_token);
}

/**
 * Custom invalidate all function that also invalidates the user data.
 */
export async function customInvalidateAll() {
  await invalidateAll();
  await invalidateUser();
}
