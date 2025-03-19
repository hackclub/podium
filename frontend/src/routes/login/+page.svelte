<!-- TODO: Migrate to new API -->
<script lang="ts">
  import { toast, Toaster } from "svelte-sonner";
  import { onMount } from "svelte";
  import { user, validateToken, signOut } from "$lib/user.svelte";
  import { AuthService, UsersService } from "$lib/client/sdk.gen";
  import { goto } from "$app/navigation";
  import type { HTTPValidationError } from "$lib/client/types.gen";
  import { handleError } from "$lib/misc";
  import type { UserSignupPayload } from "$lib/client/types.gen";
  import { countries, } from 'countries-list'
  // rest is the extra props passed to the component
  let { ...rest } = $props();

  let isLoading = $state(false);
  let showSignupFields = $state(false);
  let expandedDueTo = "";
  let userInfo: UserSignupPayload = $state({
    email: "",
    first_name: "",
    last_name: "",
    phone: "",
    street_1: "",
    street_2: "",
    city: "",
    state: "",
    zip_code: "",
    country: "",
    // https://developer.mozilla.org/en-US/docs/Web/HTML/Element/input/date
    dob: null,
  });
  $inspect(userInfo);
  let redirectUrl: string;
  
  // Convert countries to a list of objects with name and code
  const countryList = Object.entries(countries).map(([code, data]) => ({
    code,
    name: data.name,
  })).sort((a, b) => a.name.localeCompare(b.name));

  async function eitherLoginOrSignUp() {
    // If showSignupFields is true, the user is signing up and signupAndLogin should be called. Otherwise, the user is logging in and login should be called.
    if (!showSignupFields) {
      login();
    } else {
      signupAndLogin();
    }
  }

  async function checkUserExists(): Promise<boolean> {
    isLoading = true;
    try {
      const { data } = await UsersService.userExistsUsersExistsGet({
        query: { email: userInfo.email },
        throwOnError: true,
      });
      if (data?.exists) {
        showSignupFields = false;
        return true;
      } else {
        return false;
        // If the user doesn't exist, login() will toast and show the signup fields
      }
    } catch (error) {
      handleError(error);
      return false;
    } finally {
      isLoading = false;
    }
  }

  // Function to handle login
  async function login() {
    isLoading = true;
    // Even though error handling is done in the API, the try-finally block is used to ensure the loading state is reset
    try {
      const userExists = await checkUserExists();
      if (userExists) {
        // Request magic link for the provided email if the user exists
        await AuthService.requestLoginRequestLoginPost({
          body: { email: userInfo.email },
          query: { redirect: redirectUrl ?? "" },
          throwOnError: true,
        });
        toast(`Magic link sent to ${userInfo.email}`);
        // Clear field
        userInfo.email = "";
      } else {
        toast("You don't exist (yet)! Let's change that.");
        expandedDueTo = userInfo.email;
        showSignupFields = true;
      }
    } catch (error) {
      handleError(error);
    } finally {
      isLoading = false;
    }
  }

  // Function to handle signup and login
  async function signupAndLogin() {
    isLoading = true;
    try {
      await UsersService.createUserUsersPost({
        body: userInfo,
        throwOnError: true,
      });
      await login();
      // toast(`Signed up! Check your email for a magic link!`);
      // Clear values
      userInfo = {
        email: "",
        first_name: "",
        last_name: "",
        phone: "",
        street_1: "",
        street_2: "",
        city: "",
        state: "",
        zip_code: "",
        country: "",
        dob: "",
      };
    } catch (error) {
      handleError(error);
    } finally {
      isLoading = false;
    }
  }

  // Function to handle verification link
  async function verifyMagicLink(token: string) {
    isLoading = true;
    try {
      // AuthService.verifyTokenVerifyGet({query: {token}} as VerifyTokenVerifyGetData).then((response) => {
      const { data, error } = await AuthService.verifyTokenVerifyGet({
        query: { token },
        throwOnError: false,
      });
      if (error) {
        handleError(error);
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

<style>
  .card-container {
    @apply rounded-lg shadow-md bg-neutral transition-all duration-300 hover:shadow-lg;
    @apply border border-accent/20;
    @apply relative overflow-hidden;
  }

  .card-container::before {
    content: '';
    @apply absolute inset-0 bg-gradient-to-br from-accent/5 to-transparent opacity-50;
  }

  .card-container > * {
    @apply relative z-10;
  }
</style>

<div class="p-6 max-w-md mx-auto" {...rest}>
  {#if user.isAuthenticated}
    <div class="card-container p-5 text-center">
      <h2 class="text-lg font-medium mb-2">
        You are logged in as <span class="text-accent">{user.email}</span>
      </h2>
      <div class="flex justify-center gap-3 mt-3">
        <button
          class="btn btn-outline btn-accent btn-sm"
          onclick={signOut}
        >
          Sign out
        </button>
        <button
          class="btn btn-outline btn-sm"
          onclick={() => history.back()}
        >
          Go back
        </button>
      </div>
    </div>
  {:else}
    <!-- space-y-n adds space (margin) between the children -->
    <div class="card-container p-5">
      <h2 class="text-xl font-medium mb-4 text-center">Login / Sign Up</h2>
      <form onsubmit={eitherLoginOrSignUp} class="space-y-4">
        <label class="form-control">
          <div class="label">
            <span class="label-text">Email</span>
          </div>
          <input
            id="email"
            type="email"
            class="input input-bordered grow"
            bind:value={userInfo.email}
            placeholder="example@example.com"
            onblur={async () => {
              // If the signup field is expanded and the email currently entered into the field may be valid, check if the signup fields should be hidden since the user already exists
              if (
                expandedDueTo != userInfo.email &&
                userInfo.email &&
                showSignupFields
              ) {
                const userExists = await checkUserExists();
                if (userExists) {
                  showSignupFields = false;
                } else {
                  // If the user still doesn't exist, keep the signup fields open
                }
              }
            }}
          />
          <div class="label">
            <span class="label-text-alt text-opacity-75"> We'll send you a magic link </span>
          </div>
        </label>

        {#if showSignupFields}
          <label class="form-control">
            <div class="label">
              <span class="label-text">First Name</span>
            </div>
            <input
              id="first_name"
              type="text"
              class="input input-bordered grow"
              placeholder="Abc"
              bind:value={userInfo.first_name}
            />
          </label>

          <label class="form-control">
            <div class="label">
              <span class="label-text">Last Name</span>
            </div>
            <input
              id="last_name"
              type="text"
              class="input input-bordered grow"
              placeholder="Xyz"
              bind:value={userInfo.last_name}
            />
          </label>
          <label class="form-control">
            <div class="label">
              <span class="label-text">Phone</span>
              <span class="label-text-alt">
                Optional, but recommended
              </span>
            </div>
            <input
              id="phone"
              type="tel"
              class="input input-bordered grow"
              placeholder="+15555555555"
              bind:value={userInfo.phone}
            />
            <div class="label">
              <span class="label-text-alt">
                International format without spaces or special characters
              </span>
            </div>
          </label>
          <label class="form-control">
            <div class="label">
              <span class="label-text">Address line 1</span>
            </div>
            <input
              id="street_1"
              type="text"
              class="input input-bordered grow"
              placeholder="123 Main St"
              bind:value={userInfo.street_1}
            />
          </label>
          <label class="form-control">
            <div class="label">
              <span class="label-text">Address line 2</span>
              <span class="label-text-alt">Optional</span>
            </div>
            <input
              id="street_2"
              type="text"
              class="input input-bordered grow"
              placeholder="Apt 4B"
              bind:value={userInfo.street_2}
            />
          </label>
          <label class="form-control">
            <div class="label">
              <span
                class="label-text
">City</span
              >
            </div>
            <input
              id="city"
              type="text"
              class="input input-bordered grow"
              placeholder="New York"
              bind:value={userInfo.city}
            />
          </label>
          <label class="form-control">
            <div class="label">
              <span class="label-text">State/Province</span>
            </div>
            <input
              id="state"
              type="text"
              class="input input-bordered grow"
              placeholder="NY"
              bind:value={userInfo.state}
            />
          </label>
          <label class="form-control">
            <div class="label">
              <span class="label-text">Zip/Postal Code</span>
            </div>
            <input
              id="zip_code"
              type="text"
              class="input input-bordered grow"
              placeholder="10001"
              bind:value={userInfo.zip_code}
            />
          </label>
          <label class="form-control">
            <div class="label">
              <span class="label-text">Country</span>
              <!-- <span class="label-text-alt">
                <a
                  href="https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2"
                  class="underline">ISO 3166-1 alpha-2</a
                >
              </span> -->
            </div>
            <select
              id="country"
              class="select select-bordered grow"
              bind:value={userInfo.country}
            >
              {#each countryList as { code, name } (code)}
                <option value={code} selected={userInfo.country == code}>
                  {name}
                </option>
              {/each}
            </select>
          </label>
          <label class="form-control">
            <div class="label">
              <span class="label-text">Date of Birth</span>
              <span class="label-text-alt"
                >Hack Club is only for students {"<="}18</span
              >
            </div>
            <input
              id="dob"
              type="date"
              class="input input-bordered grow"
              bind:value={userInfo.dob}
            />
          </label>
        {/if}
        <div class="flex justify-center">
          <button type="submit" class="btn btn-accent btn-outline hover:bg-accent/20 mt-2" disabled={isLoading}>
            {isLoading ? 'Processing...' : 'Login / Sign Up'}
          </button>
        </div>
      </form>
    </div>
  {/if}
  <!-- TODO: Make this use a var -->
  <div class="text-center mt-4">
    <a href="/" class="btn btn-sm btn-outline">← Back to Home</a>
  </div>
</div>
