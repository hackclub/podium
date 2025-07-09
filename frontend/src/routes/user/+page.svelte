<script lang="ts">
  import type { PageData } from "./$types";
  import { getAuthenticatedUser } from "$lib/user.svelte";
  let { data }: { data: PageData } = $props();
</script>

<div class="max-w-6xl mx-auto space-y-8">
  <div class="mb-8">
    <h1 class="text-3xl font-bold text-base-content mb-2">
      Hello, {getAuthenticatedUser().user.first_name}!
    </h1>
    <p class="text-base-content/70">Welcome to your profile page. Here you can view all your projects and manage your account.</p>
  </div>

  <!-- User Info Card -->
  <div class="card bg-base-100 shadow-lg">
    <div class="card-body">
      <h2 class="card-title text-xl mb-4">Profile Information</h2>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <div class="label">
            <span class="label-text font-semibold">First Name</span>
          </div>
          <div class="input input-bordered w-full bg-base-200">
            {getAuthenticatedUser().user.first_name}
          </div>
        </div>
        <div>
          <div class="label">
            <span class="label-text font-semibold">Last Name</span>
          </div>
          <div class="input input-bordered w-full bg-base-200">
            {getAuthenticatedUser().user.last_name}
          </div>
        </div>
        <div class="md:col-span-2">
          <div class="label">
            <span class="label-text font-semibold">Email</span>
          </div>
          <div class="input input-bordered w-full bg-base-200">
            {getAuthenticatedUser().user.email}
          </div>
        </div>
      </div>
    </div>
  </div>
</div>
