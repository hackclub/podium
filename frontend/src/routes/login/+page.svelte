<script lang="ts">
  import { defaultUser, getAuthenticatedUser } from "$lib/user.svelte";
  import { toast, Toaster } from "svelte-sonner";
  import { onMount } from "svelte";
  import { validateToken } from "$lib/user.svelte";
  import { AuthService, UsersService } from "$lib/client/sdk.gen";
  import { goto } from "$app/navigation";
  import type { HTTPValidationError } from "$lib/client/types.gen";
  import { handleError } from "$lib/misc";
  import type { UserSignupPayload } from "$lib/client/types.gen";
  import { countries } from "countries-list";
  // rest is the extra props passed to the component
  let { ...rest } = $props();

  let isLoading = $state(false);
  let showSignupFields = $state(false);
  let expandedDueTo = "";
  let userInfo: UserSignupPayload = $state({
    ...defaultUser,
  });
  $inspect(userInfo);
  $inspect(showSignupFields);
  let redirectUrl: string;

  // Convert countries to a list of objects with name and code
  const countryList = Object.entries(countries)
    .map(([code, data]) => ({
      code,
      name: data.name,
    }))
    .sort((a, b) => a.name.localeCompare(b.name));

  async function eitherLoginOrSignUp() {
    // console.debug("eitherLoginOrSignUp", showSignupFields);
    // If showSignupFields is true, the user is signing up and signupAndLogin should be called. Otherwise, the user is logging in and login should be called.
    if (!showSignupFields) {
      login();
    } else {
      signupAndLogin();
    }
  }

  async function checkUserExists(): Promise<boolean> {
    isLoading = true;
    const { data, error: err } = await UsersService.userExistsUsersExistsGet({
      query: { email: userInfo.email },
      throwOnError: false,
    });
    isLoading = false;
    if (err || !data) {
      handleError(err);
      return false;
    }
    if (data.exists) {
      showSignupFields = false;
      return true;
    } else {
      return false;
      // If the user doesn't exist, login() will toast and show the signup fields
    }
  }

  // Function to handle login
  async function login() {
    isLoading = true;
    // Stop immediately if no email was entered to avoid backend validation popups
    if (!userInfo.email || userInfo.email.trim() === "") {
      isLoading = false;
      toast.error("Please enter your email address.");
      document.getElementById("email")?.focus();
      return;
    }
    // Even though error handling is done in the API, the try-finally block is used to ensure the loading state is reset
    const userExists = await checkUserExists();
    if (userExists) {
      // Request magic link for the provided email if the user exists
      const { error: err } = await AuthService.requestLoginRequestLoginPost({
        body: { email: userInfo.email },
        query: { redirect: redirectUrl ?? "" },
        throwOnError: false,
      });
      isLoading = false;
      if (err) {
        handleError(err);
        return;
      }
      toast.success(`Magic link sent to ${userInfo.email}`);
      // Clear field
      userInfo.email = "";
    } else {
      toast.error("You don't exist (yet)! Let's change that.");
      expandedDueTo = userInfo.email;
      showSignupFields = true;
    }
  }

  // Function to handle signup and login
  async function signupAndLogin() {
    isLoading = true;
    if (!userInfo.email || userInfo.email.trim() === "") {
      isLoading = false;
      toast.error("Please enter your email address.");
      document.getElementById("email")?.focus();
      return;
    }
    // Generate display name if not provided or only whitespace
    if (!userInfo.display_name || userInfo.display_name.trim() === "") {
      const first = userInfo.first_name?.trim() || "";
      const lastInitial = userInfo.last_name?.trim()
        ? userInfo.last_name.trim()[0] + "."
        : "";
      userInfo.display_name = `${first} ${lastInitial}`.trim();
    }
    const { error: err } = await UsersService.createUserUsersPost({
      body: userInfo,
      throwOnError: false,
    });
    isLoading = false;
    if (err) {
      handleError(err);
      return;
    }
    await login();
    // toast(`Signed up! Check your email for a magic link!`);
    // Clear values
    userInfo = {
      ...defaultUser,
    };
  }

  // Function to handle verification link
  async function verifyMagicLink(token: string) {
    isLoading = true;
    try {
      // AuthService.verifyTokenVerifyGet({query: {token}} as VerifyTokenVerifyGetData).then((response) => {
      const { data, error: err } = await AuthService.verifyTokenVerifyGet({
        query: { token },
        throwOnError: false,
      });
      if (err || !data) {
        handleError(err);
        return;
      } else {
        // Store the token in localStorage
        localStorage.setItem("token", data.access_token);
        // console.log('Token passed, set, and verified successfully', response);
        // Just verify the new token since that will store it too. If this isn't valid, there's an issue since that means the server is returning a bad token.
        await validateToken(data.access_token);
        toast("Login successful");

        // Redirect to the original URL if present
        if (redirectUrl) {
          goto(redirectUrl);
        } else {
          goto("/");
        }
      }
    } finally {
      isLoading = false;
    }
  }

  // Check for token in URL on mount
  // For example: /login?token=abc123
  onMount(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const token = urlParams.get("token");
    redirectUrl = urlParams.get("redirect") ?? "";
    if (token) {
      console.log("Token found in URL:", token);
      verifyMagicLink(token);
    }
  });

  // Prevent default form submission (not needed it seems)
  // https://svelte.dev/docs/svelte/svelte-legacy#preventDefault
  // https://svelte.dev/docs/svelte/v5-migration-guide#Breaking-changes-in-runes-mode-Touch-and-wheel-events-are-passive
  // function preventDefault(fn) {
  //     return function (event) {
  //         event.preventDefault();
  //         fn.call(this, event);
  //     };
  // }
</script>

<div class="p-4 max-w-md mx-auto" {...rest}>
  {#if getAuthenticatedUser().access_token}
    <div class="text-center">
      <h2 class="text-2xl font-bold mb-2">
        You are logged in as {getAuthenticatedUser().user.email}
      </h2>
      <button
        class="mt-4 px-4 py-2 btn btn-primary"
        onclick={() => history.back()}
      >
        Go back to previous page
      </button>
    </div>
  {:else}
    <fieldset
      class="fieldset bg-base-200 border-base-300 rounded-box border p-4"
    >
      <label class="label flex justify-between" for="email">
        <span>Email</span>
      </label>
      <input
        id="email"
        type="email"
        class="input input-bordered w-full"
        bind:value={userInfo.email}
        placeholder="example@example.com"
        onblur={async () => {
          if (
            expandedDueTo != userInfo.email &&
            userInfo.email &&
            showSignupFields
          ) {
            const userExists = await checkUserExists();
            if (userExists) {
              showSignupFields = false;
            }
          }
        }}
      />
      <label class="label flex justify-between" for="email">
        <span>We'll send you an email</span>
      </label>

      {#if showSignupFields}
        <label class="label" for="first_name">First Name</label>
        <input
          id="first_name"
          type="text"
          class="input input-bordered w-full"
          placeholder="Abc"
          bind:value={userInfo.first_name}
        />

        <label class="label" for="last_name">Last Name</label>
        <input
          id="last_name"
          type="text"
          class="input input-bordered w-full"
          placeholder="Xyz"
          bind:value={userInfo.last_name}
        />

        <!-- Display name; if it's not set, use first name and last initial -->
        <label class="label flex justify-between" for="display_name">
          <span>Display Name</span>
          <span>Optional, default is First Name + Last Initial</span>
        </label>
        <input
          id="display_name"
          type="text"
          class="input input-bordered w-full"
          placeholder="Abc X."
          bind:value={userInfo.display_name}
        />
        <!-- Removed display name preview -->

        <label class="label flex justify-between" for="phone">
          <span>Phone</span>
          <span>Optional, but recommended</span>
        </label>
        <input
          id="phone"
          type="tel"
          class="input input-bordered w-full"
          placeholder="+15555555555"
          bind:value={userInfo.phone}
        />
        <label class="label flex justify-between" for="phone">
          <span>International format without spaces or special characters</span>
        </label>

        <label class="label" for="street_1">Address line 1</label>
        <input
          id="street_1"
          type="text"
          class="input input-bordered w-full"
          placeholder="123 Main St"
          bind:value={userInfo.street_1}
        />

        <label class="label flex justify-between" for="street_2">
          <span>Address line 2</span>
          <span>Optional</span>
        </label>
        <input
          id="street_2"
          type="text"
          class="input input-bordered w-full"
          placeholder="Apt 4B"
          bind:value={userInfo.street_2}
        />

        <label class="label" for="city">City</label>
        <input
          id="city"
          type="text"
          class="input input-bordered w-full"
          placeholder="New York"
          bind:value={userInfo.city}
        />

        <label class="label" for="state">State/Province</label>
        <input
          id="state"
          type="text"
          class="input input-bordered w-full"
          placeholder="NY"
          bind:value={userInfo.state}
        />

        <label class="label" for="zip_code">Zip/Postal Code</label>
        <input
          id="zip_code"
          type="text"
          class="input input-bordered w-full"
          placeholder="10001"
          bind:value={userInfo.zip_code}
        />

        <label class="label" for="country">Country</label>
        <select
          id="country"
          class="select select-bordered w-full"
          bind:value={userInfo.country}
        >
          {#each countryList as { code, name } (code)}
            <option value={code} selected={userInfo.country == code}>
              {name}
            </option>
          {/each}
        </select>

        <label class="label flex justify-between" for="dob">
          <span>Date of Birth</span>
          <span>Hack Club is only for students {"<="}18</span>
        </label>
        <input
          id="dob"
          type="date"
          class="input input-bordered w-full"
          bind:value={userInfo.dob}
        />
      {/if}

      <div class="flex justify-center">
        <button
          class="btn btn-primary mt-4"
          disabled={isLoading}
          onclick={eitherLoginOrSignUp}
        >
          Login / Sign Up
        </button>
      </div>
    </fieldset>
  {/if}
  <div class="text-center mt-4">
    <a href="/" class="btn-sm btn-secondary btn">← Back Home</a>
  </div>
</div>
