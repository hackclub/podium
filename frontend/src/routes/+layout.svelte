<script lang="ts">
  import "../app.css";
  import { Toaster } from "svelte-sonner";
  import { navigating, page } from "$app/state";
  let { children } = $props();
  import { onMount, onDestroy } from "svelte";
  import { themeChange } from "theme-change";
  import ThemeSwitcher from "$lib/components/ThemeSwitcher.svelte";
  import { setSystemTheme, returnLoadingText } from "$lib/misc";
  import Modal from "$lib/components/Modal.svelte";
  let aboutModal: Modal = $state() as Modal;
  let loadingText = $state(returnLoadingText());
  let loadingTextInterval: NodeJS.Timeout = $state() as NodeJS.Timeout;
  onMount(() => {
    console.debug("Page data:", page.data);
    themeChange(false);
    setSystemTheme();

    // Update loading text every 4 seconds
    loadingTextInterval = setInterval(() => {
      loadingText = returnLoadingText();
    }, 4000);
  });

  onDestroy(() => {
    clearInterval(loadingTextInterval);
  });

  const navOptions = {
    "/projects": "Projects",
    "/events": "Events",
  };
</script>

<svelte:head>
  <title>{page.data.title ? `${page.data.title} | Podium` : 'Podium'}</title>
  {#if page.data.meta}
    {#each page.data.meta as { name, content }}
      <meta {name} {content} />
    {/each}
  {/if}
</svelte:head>

<div class="drawer">
  <input id="my-drawer-3" type="checkbox" class="drawer-toggle" />
  <div class="drawer-content flex flex-col">
    <!-- Navbar -->
    <div class="navbar bg-base-300 w-full">
      <div class="flex-none lg:hidden">
        <label
          for="my-drawer-3"
          aria-label="open sidebar"
          class="btn btn-square btn-ghost"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            class="inline-block h-6 w-6 stroke-current"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M4 6h16M4 12h16M4 18h16"
            ></path>
          </svg>
        </label>
      </div>
      <div class="mx-2 flex-1 px-2"><a href="/" class="font-extrabold">Podium</a></div>
      <div class="hidden flex-none lg:block">
        <ul class="menu menu-horizontal">
          {#each Object.entries(navOptions) as [path, label]}
            <li>
              <a href={path}>{label}</a>
            </li>
          {/each}
        </ul>
      </div>
    </div>
    <!--------- start of page content --------->
    <!-- flex-1 makes it take up the entire space. Without the div with flex-1 the width was too small -->
    <div class="flex-1">
    <div class="p-4 bg-info text-center rounded-xl max-w-2xl mx-auto m-4">
      <p class="text-info-content">
        Podium isn't working and need urgent help? DM @Angad Behl on Slack or
        call +1 (415) 570-4995.
      </p>
    </div>

    {#if navigating.to && navigating.type != "form"}
      <div class="flex items-center justify-center min-h-screen flex-col">
        <span class="loading loading-ball loading-lg mb-2"></span>
        <p>{loadingText}</p>
      </div>
    {:else}
      {@render children()}
    {/if}

    <div class="fixed bottom-4 left-4">
      <!-- Info Button -->
      <button
        class="btn btn-info btn-square btn-md font-serif font-light"
        aria-label="Info"
        onclick={() => {
          aboutModal.openModal();
        }}
      >
        ?
      </button>
    </div>

    <Modal bind:this={aboutModal} title="About Podium">
      <p class="py-4">
        Podium is <a href="https://hackclub.com" class="hover-link"
          >Hack Club's
        </a> <a href="https://github.com/hackclub/podium" class="hover-link"
          >open-source</a
        >
        peer-judging platform for
        <a href="https://hackathons.hackclub.com/" class="hover-link"
          >hackathons</a
        >. If you encounter issues, feel free to
        <a href="https://github.com/hackclub/podium/issues" class="hover-link"
          >report</a
        >
        them. Need help? Ask on the
        <a href="https://hackclub.com/slack" class="hover-link">Slack</a>
        or email
        <a href="mailto:angad@hackclub.com" class="hover-link"
          >angad@hackclub.com</a
        >.
      </p>
      <p class="text-right">
        <a href="https://github.com/slashtechno" class="hover-link"
          >-Angad Behl</a
        >
      </p>
    </Modal>

    <div class="fixed bottom-4 right-4">
      <ThemeSwitcher />
    </div>
    <Toaster />
</div> 
    <!--------- end of page content --------->
  </div>
  <div class="drawer-side">
    <label for="my-drawer-3" aria-label="close sidebar" class="drawer-overlay"
    ></label>
    <ul class="menu bg-base-200 min-h-full w-80 p-4">
      <!-- Sidebar content here -->
      {#each Object.entries(navOptions) as [path, label]}
        <li>
          <a href={path}>{label}</a>
        </li>
      {/each}
    </ul>
  </div>
</div>
