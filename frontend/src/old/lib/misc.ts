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
  console.error("Error", error);
  if (error && typeof error === "object") {
    if ("error" in error && typeof (error as any).error === "string") {
      const msg = (error as any).error as string;
      if (msg.toLowerCase().includes("rate limit")) {
        toast.error("Too many requests. Please wait a moment and try again.");
        return;
      }
    }
    if ("detail" in error) {
      if (Array.isArray(error?.detail)) {
        const invalidFields = (error as any).detail.map(
          (e: any) => `${e.loc.join(".")}: ${e.msg}`,
        );
        toast.error(invalidFields.join(" | "));
      } else if (typeof (error as any)?.detail === "string") {
        const detail = (error as any).detail as string;
        if (detail.toLowerCase().includes("rate limit")) {
          toast.error("Too many requests. Please wait a moment and try again.");
        } else {
          toast.error(detail);
        }
      }
      return;
    }
  }
  if (error instanceof Error) {
    toast.error(error.message);
  } else {
    toast.error("An error occurred, check the console for more details");
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
