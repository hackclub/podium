<svelte:options runes />

<script lang="ts">
  import Icon from "@iconify/svelte";
  import { user, signOut } from "$lib/user.svelte";
</script>

<div class="max-w-5xl mx-auto py-8 px-6">
  <!-- Welcome Hero Section -->
  <section class="mb-10 text-center">
    <h1 class="text-3xl font-medium mb-3">Podium</h1>
    <p class="text-lg opacity-80 max-w-2xl mx-auto">
      Hack Club's open-source peer-judging platform for hackathons. Angad, add something here.
    </p>
  </section>

  <div class="grid gap-8">
    <!-- Login Card - Smaller when logged in -->
    <div class="grid md:grid-cols-3 gap-8">
      <section class="card-container md:col-span-{user.isAuthenticated ? '1' : '3'}">
        <h2 class="text-xl font-medium mb-3">Account</h2>
        {#if user.isAuthenticated}
          <div class="py-3">
            <p class="mb-3 text-sm">
              Signed in as <span class="font-medium">{user.email}</span>
            </p>
            <button class="btn btn-outline btn-accent btn-sm hover:bg-accent/20 w-full" onclick={signOut}>Sign out</button>
          </div>
        {:else}
          <div class="flex justify-center py-4">
            <a href="/login" class="btn btn-accent btn-outline hover:bg-accent/20 px-8">Login / Sign Up</a>
          </div>
        {/if}
      </section>

      {#if user.isAuthenticated}
        <!-- Quick Stats Section -->
        <section class="card-container md:col-span-2">
          <h2 class="text-xl font-medium mb-3">Your Activity... Honestly it just exists because the dashboard looks bland af. We should probably add scrapyard or hackathons.hackclub.com banner</h2>
          <div class="grid grid-cols-2 gap-4 py-3">
            <div class="text-center">
              <div class="stat-value text-2xl text-accent">0</div>
              <div class="stat-title text-sm opacity-70">Projects</div>
            </div>
            <div class="text-center">
              <div class="stat-value text-2xl text-accent">0</div>
              <div class="stat-title text-sm opacity-70">Events</div>
            </div>
          </div>
        </section>
      {/if}
    </div>

    <!-- Main Dashboard Cards -->
    <div class="grid gap-8 md:grid-cols-2">
      <section class="card-container">
        <h2 class="text-xl font-medium mb-3">Events</h2>
        <p class="text-sm opacity-80 mb-4">Join hackathons, submit your projects, and vote on other submissions idk maybe break stuff too /shrug</p>
        <div class="flex justify-center">
          <a href="/events" class="dashboard-btn">
            <span>Events Dashboard</span>
            <Icon icon="material-symbols:arrow-right-alt-rounded" style="font-size: 24px;" />
          </a>
        </div>
      </section>
      
      <section class="card-container">
        <h2 class="text-xl font-medium mb-3">Projects</h2>
        <p class="text-sm opacity-80 mb-4">VOTEEEEEEE. I LOVE DEMOCRACY ESP WHEN IT IS FUNCTIONAL</p>
        <div class="flex justify-center">
          <a href="/projects" class="dashboard-btn">
            <span>Projects Dashboard</span>
            <Icon icon="material-symbols:arrow-right-alt-rounded" style="font-size: 24px;" />
          </a>
        </div>
      </section>
    </div>

    <!-- Featured Section -->
    <section class="card-container mt-4">
      <h2 class="text-xl font-medium mb-3">Getting Started</h2>
      <div class="grid md:grid-cols-3 gap-6 py-2">
        <div class="feature-card">
          <div class="text-accent mb-2">1</div>
          <h3 class="font-medium mb-1">Create Account</h3>
          <p class="text-sm opacity-80">Because we neeed record id and stuff</p>
        </div>
        <div class="feature-card">
          <div class="text-accent mb-2">2</div>
          <h3 class="font-medium mb-1">Join an Event</h3>
          <p class="text-sm opacity-80">Participate in hackathons because they're really cool</p>
        </div>
        <div class="feature-card">
          <div class="text-accent mb-2">3</div>
          <h3 class="font-medium mb-1">Submit Projects</h3>
          <p class="text-sm opacity-80">Showcase your work & get prizes maybe? Esp if you win</p>
        </div>
      </div>
    </section>
  </div>
</div>

<style>
  .card-container {
    @apply p-6 rounded-lg shadow-md bg-neutral transition-all duration-300 hover:shadow-lg;
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

  .dashboard-btn {
    @apply btn btn-outline btn-accent hover:bg-accent/20 w-full max-w-xs flex items-center justify-center transition-all duration-300;
  }

  .feature-card {
    @apply p-4 rounded-md bg-base-300/30 border border-accent/10;
  }

  * {
    @apply text-neutral-content;
  }
</style>
