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

function randomFromArray<T>(arr: T[]): T {
  return arr[Math.floor(Math.random() * arr.length)];
}

function randomInt(min: number, max: number) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

function randomId(length = 12) {
  return [...Array(length)].map(() => Math.random().toString(36)[2]).join("");
}

export function generateUser() {
  const firstNames = ["Alice", "Bob", "Charlie", "Dana", "Elliot", "Fiona"];
  const lastNames = ["Smith", "Johnson", "Lee", "Garcia", "Brown", "Taylor"];
  const streets = ["Main St", "Oak Ave", "Pine Rd", "Maple Blvd"];
  const cities = ["New York", "Los Angeles", "Chicago", "Seattle"];
  const states = ["NY", "CA", "IL", "WA"];
  const countries = ["USA", "Canada"];

  const first_name = randomFromArray(firstNames);
  const last_name = randomFromArray(lastNames);
  const email = `${first_name.toLowerCase()}.${last_name.toLowerCase()}@example.com`;
  const phone = `+1${randomInt(2000000000, 9999999999)}`;

  const street_1 = `${randomInt(100, 9999)} ${randomFromArray(streets)}`;
  const street_2 = Math.random() < 0.5 ? `Apt ${randomInt(1, 999)}` : null;
  const city = randomFromArray(cities);
  const state = randomFromArray(states);
  const zip_code = `${randomInt(10000, 99999)}`;
  const country = randomFromArray(countries);

  const year = randomInt(2008, 2020);
  const month = String(randomInt(1, 12)).padStart(2, "0");
  const day = String(randomInt(1, 28)).padStart(2, "0");
  const dob = `${year}-${month}-${day}`;

  return {
    first_name,
    last_name,
    email,
    phone,
    street_1,
    street_2,
    city,
    state,
    zip_code,
    country,
    dob,
    id: randomId(),
    votes: [],
    projects: [],
    collaborations: [],
    owned_events: [],
    attending_events: [],
    referral: [],
  };
}
