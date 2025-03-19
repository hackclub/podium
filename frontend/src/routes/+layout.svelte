<script lang="ts">
  import "../app.css";
  import { Toaster } from "svelte-sonner";
  import { navigating, page } from "$app/state";
  let { children } = $props();
  import { onMount } from "svelte";
  import { themeChange } from "theme-change";
  import ThemeSwitcher from "$lib/components/ThemeSwitcher.svelte";
  import { setSystemTheme, returnLoadingText } from "$lib/misc";
  // import CheckAuth from '$lib/components/CheckAuth.svelte';

  onMount(() => {
    console.debug("Page data:", page.data);
    themeChange(false);

    setSystemTheme();
  });

  let showModal = $state(false);
</script>

<svelte:head>
  {#if page.data.title}
    <title>{page.data.title} | Podium</title>
  {/if}
  {#if page.data.meta}
    {#each page.data.meta as { name, content }}
      <meta {name} {content} />
    {/each}
  {/if}
</svelte:head>

<header class="sticky top-0 z-50 shadow-md bg-neutral">
  <div class="container mx-auto px-4">
    <nav class="flex justify-between items-center py-4">
      <a href="/" class="text-3xl font-bold text-neutral-content">Podium</a>
      <div class="flex space-x-6">
        <a href="/projects" class="text-neutral-content hover:text-accent text-lg font-medium transition-colors duration-200">Projects</a>
        <a href="/events" class="text-neutral-content hover:text-accent text-lg font-medium transition-colors duration-200">Events</a>
      </div>
    </nav>
  </div>
</header>

<div class="container mx-auto px-4 py-6">
  <div class="bg-info/80 text-center rounded-lg p-3 mb-8 shadow-sm max-w-4xl mx-auto backdrop-blur-sm border border-info/20">
    <p class="text-info-content text-sm">
      Welcome to Scrapyard! Need help? Send a message in <a href="h" class="font-medium underline">#scrapyard-support</a>. Podium isn't working? DM <a href="s" class="font-medium underline">@Angad Behl</a> on Slack or call <span class="font-medium">+1 (415) 570-4995</span>
    </p>
  </div>

  {#if navigating.to && navigating.type != "form"}
    <div class="flex items-center justify-center min-h-[60vh] flex-col">
      <span class="loading loading-ball loading-lg mb-4"></span>
      <p class="text-lg">{returnLoadingText()}</p>
    </div>
  {:else}
    <main class="min-h-[70vh]">
      {@render children()}
    </main>
  {/if}
</div>

<div class="fixed bottom-6 left-6">
  <!-- Info Button -->
  <button
    class="btn btn-info btn-circle btn-lg font-serif font-light shadow-lg"
    aria-label="Info"
    onclick={() => {
      showModal = true;
    }}
  >
    i
  </button>
</div>

<!-- Modal -->
{#if showModal}
  <div class="modal modal-open modal-bottom sm:modal-middle">
    <div class="modal-box max-w-2xl">
      <h2 class="font-bold text-xl mb-4">About the Project</h2>
      <p class="py-4 text-base">
        Podium is <a href="https://hackclub.com" class="hover-link">Hack Club's </a><a
          href="https://github.com/hackclub/podium" class="hover-link">open-source</a
        >
        peer-judging platform for
        <a href="https://hackathons.hackclub.com/" class="hover-link">hackathons</a>. If you
        encounter issues, feel free to
        <a href="https://github.com/hackclub/podium/issues" class="hover-link">report</a> them.
        Need help? Ask on the <a href="https://hackclub.com/slack" class="hover-link">Slack</a> or
        email <a href="mailto:angad@hackclub.com" class="hover-link">angad@hackclub.com</a>.
      </p>
      <p class="text-right mt-4">
        <a href="https://github.com/slashtechno" class="hover-link">-Angad Behl</a>
      </p>
      <div class="modal-action">
        <button
          class="btn btn-primary"
          onclick={() => {
            showModal = false;
          }}>Close</button
        >
      </div>
    </div>
  </div>
{/if}

<div class="fixed bottom-6 right-32">
  <ThemeSwitcher />
</div>

<!-- All pages should be able to show toasts -->
<Toaster />
