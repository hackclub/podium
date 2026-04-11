<script lang="ts">
  import { defaultUser, getAuthenticatedUser } from "$lib/user.svelte";
  import { toast, Toaster } from "svelte-sonner";
  import { onMount } from "svelte";
  import { validateToken } from "$lib/user.svelte";
  import { AuthService, UsersService } from "$lib/client/sdk.gen";
  import { goto } from "$app/navigation";
  import type { HTTPValidationError } from "$lib/client/types.gen";
  import { handleError } from "$lib/misc";
  import type { UserSignup } from "$lib/client/types.gen";
  import { countries } from "countries-list";
  import { asyncClick } from "$lib/actions/asyncClick";
  import { Turnstile } from "svelte-turnstile";
  import { env } from "$env/dynamic/public";
  // rest is the extra props passed to the component
  let { ...rest } = $props();

  // Turnstile token — refreshed each time the user solves the challenge
  let turnstileToken = $state("");

  let isVerifying = $state(false);
  let showSignupFields = $state(false);
  let expandedDueTo = "";
  let userInfo: UserSignup = $state({
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
      await login();
    } else {
      await signupAndLogin();
    }
  }

  /** Build headers including the Turnstile token when one is available. */
  function turnstileHeaders(): Record<string, string> {
    return turnstileToken ? { "X-Turnstile-Token": turnstileToken } : {};
  }

  async function checkUserExists(): Promise<boolean> {
    const { data, error: err } = await UsersService.userExistsUsersExistsGet({
      query: { email: userInfo.email },
      headers: turnstileHeaders(),
      throwOnError: false,
    });
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
    if (!userInfo.email || userInfo.email.trim() === "") {
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
        headers: turnstileHeaders(),
        throwOnError: false,
      });
      if (err) {
        handleError(err);
        return;
      }
      toast.success(`Magic link sent to ${userInfo.email}. Check your spam folder if you don't see it!`);
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
    if (!userInfo.email || userInfo.email.trim() === "") {
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
    const signupEmail = userInfo.email;
    const { error: signupErr } = await UsersService.createUserUsersPost({
      body: userInfo,
      headers: turnstileHeaders(),
      throwOnError: false,
    });
    if (signupErr) {
      handleError(signupErr);
      return;
    }

    // Request magic link immediately after signup without re-checking existence
    const { error: loginErr } = await AuthService.requestLoginRequestLoginPost({
      body: { email: signupEmail },
      query: { redirect: redirectUrl ?? "" },
      headers: turnstileHeaders(),
      throwOnError: false,
    });
    if (loginErr) {
      handleError(loginErr);
      return;
    }

    showSignupFields = false;
    expandedDueTo = "";
    toast.success(`Magic link sent to ${signupEmail}. Check your spam folder if you don't see it!`);
    // Reset values for the next signup attempt
    userInfo = {
      ...defaultUser,
    };
  }

  // Function to handle verification link
  async function verifyMagicLink(token: string) {
    isVerifying = true;
    try {
      const { data, error: err } = await AuthService.verifyTokenVerifyGet({
        query: { token },
        throwOnError: false,
      });
      if (err || !data) {
        handleError(err);
        return;
      }
      localStorage.setItem("token", data.access_token);
      await validateToken(data.access_token);
      toast("Login successful");

      const target = redirectUrl && redirectUrl.trim() !== "" ? redirectUrl : "/";
      await goto(target);
    } finally {
      isVerifying = false;
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
  {:else if isVerifying}
    <div class="text-center">
      <span class="loading loading-spinner loading-lg"></span>
      <p class="mt-2">Verifying your magic link...</p>
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

      {#if env.PUBLIC_TURNSTILE_SITE_KEY}
        <div class="flex justify-center mt-4">
          <Turnstile
            siteKey={env.PUBLIC_TURNSTILE_SITE_KEY}
            theme="auto"
            on:callback={(e) => (turnstileToken = e.detail.token)}
            on:expired={() => (turnstileToken = "")}
            on:timeout={() => (turnstileToken = "")}
          />
        </div>
      {/if}

      <div class="flex justify-center">
        <button
          class="btn btn-primary mt-4"
          disabled={!!env.PUBLIC_TURNSTILE_SITE_KEY && !turnstileToken}
          use:asyncClick={eitherLoginOrSignUp}
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
