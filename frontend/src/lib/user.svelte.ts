import { client, UsersService } from "$lib/client/sdk.gen";
import { AuthService } from "$lib/client/sdk.gen";
import type { AuthenticatedUser, UserPrivate } from "./client";

export const defaultUser: UserPrivate = {
  first_name: "",
  last_name: "",
  email: "",
  phone: "",
  street_1: null,
  street_2: null,
  city: null,
  state: null,
  zip_code: null,
  country: null,
  dob: null,
  id: "",
  votes: [],
  projects: [],
  collaborations: [],
  owned_events: [],
  attending_events: [],
  referral: [],
};

export const defaultAuthenticatedUser: AuthenticatedUser = {
  access_token: "",
  token_type: "",
  user: defaultUser,
};

let user: AuthenticatedUser = $state(defaultAuthenticatedUser);
export function getAuthenticatedUser(): AuthenticatedUser {
  return user;
}
export function setAuthenticatedUser(newUser: AuthenticatedUser) {
  user = newUser;
}

export function signOut() {
  user = defaultAuthenticatedUser;
  localStorage.removeItem("token");
  client.setConfig({
    headers: {
      Authorization: "",
    },
  });
  console.debug(
    "User signed out, cleared user state, token in localStorage and headers",
  );
}

export function validateToken(token: string): Promise<void> {
  return UsersService.getCurrentUserInfoUsersCurrentGet({
    headers: {
      Authorization: `Bearer ${token}`,
    },
    throwOnError: false,
  })
    .then((response) => {
      if (response.error || !response.data) {
        console.error("Invalid token", response);
        throw new Error("Invalid token");
      }
      user = {
        access_token: token,
        token_type: "Bearer",
        user: response.data,
      };
      client.setConfig({
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      console.debug("Token verified, set user state and headers");
    })
    .catch((err) => {
      console.log("Token is invalid", err);
      signOut();
    });
}
