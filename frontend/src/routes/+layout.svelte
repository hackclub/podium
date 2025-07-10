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
  import { goto } from "$app/navigation";
  let aboutModal: Modal = $state() as Modal;
  let loadingText = $state(returnLoadingText());
  let loadingTextInterval: NodeJS.Timeout = $state() as NodeJS.Timeout;

  // Reactive variables for meta tags to ensure they update properly
  const title = $derived(page.data.title ? `${page.data.title} | Podium` : 'Podium');
  const description = $derived(
    page.data.meta?.find((m: { name: string; }) => m.name === 'description')?.content || 
    "Podium - Hack Club's open-source peer-judging platform for hackathons"
  );
  const additionalMeta = $derived(
    page.data.meta?.filter((m: { name: string; }) => m.name !== 'description') || []
  );

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

  import { getAuthenticatedUser } from "$lib/user.svelte";

  const navOptions = {
    "/": "Dashboard",
  };

  // Event sub-navigation options
  const eventSubNav = {
    "/events": "My Events",
    "/events/attend": "Attend Event", 
    "/events/create": "Create Event",
  };

  // Project sub-navigation options  
  const projectSubNav = {
    "/projects": "My Projects",
    "/projects/create": "Create Project",
    "/projects/join": "Join Project",
  };

  // State for dropdown toggles
  let projectsExpanded = $state(false);
  let eventsExpanded = $state(false);

  // State for immediate click feedback
  let projectsClicked = $state(false);
  let eventsClicked = $state(false);

  // Helper function to check if current path matches a section
  const isInSection = (section: string) => {
    return page.url.pathname.startsWith(section);
  };

  // Auto-expand/collapse relevant section based on current path
  $effect(() => {
    // Projects: unfold if on /projects path, fold if not
    projectsExpanded = isInSection('/projects');
    
    // Events: unfold if on /events path, fold if not
    eventsExpanded = isInSection('/events');

    // Reset click states when navigation completes
    projectsClicked = false;
    eventsClicked = false;
  });
</script>

<svelte:head>
  <title>{title}</title>
  <meta name="description" content={description} />
  {#each additionalMeta as { name, content }}
    <meta {name} {content} />
  {/each}
</svelte:head>

        <Toaster
        toastOptions={{
            unstyled: true,
            class: "toast alert",
            classes: {
              success: "alert-success",
              error: "alert-error",
              info: "alert-info",
              warning: "alert-warning",
              closeButton: "btn btn-sm btn-circle btn-ghost btn-error",
              cancelButton: "btn btn-sm btn-circle btn-ghost btn-error",
            }
        }} closeButton/>

{#if page.url.pathname !== '/login'}
<!-- Sidebar Layout for authenticated users -->
<div class="drawer lg:drawer-open">
  <input id="sidebar-drawer" type="checkbox" class="drawer-toggle" />
  <div class="drawer-content flex flex-col">
    <!-- Top Navbar -->
    <div class="navbar bg-base-200 lg:hidden">
      <div class="flex-none">
        <label for="sidebar-drawer" aria-label="open sidebar" class="btn btn-square btn-ghost">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" class="inline-block h-6 w-6 stroke-current">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"></path>
          </svg>
        </label>
      </div>
      <div class="flex-1">
        <a href="/" class="btn btn-ghost text-xl font-extrabold">Podium</a>
      </div>
      <div class="flex-none">
        <ThemeSwitcher />
      </div>
    </div>
    
    <!-- Main Content -->
    <div class="flex-1 p-6">
      <div class="bg-info text-center rounded-xl max-w-2xl mx-auto mb-6 p-4">
        <p class="text-info-content">
          Podium isn't working and need urgent help? DM @Angad Behl on Slack or call +1 (415) 570-4995.
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
    </div>
  </div>
  
  <!-- Sidebar -->
  <div class="drawer-side">
    <label for="sidebar-drawer" aria-label="close sidebar" class="drawer-overlay"></label>
    <div class="min-h-full w-80 bg-base-200 flex flex-col">
      <!-- Logo/Header -->
      <div class="p-6 border-b border-base-300">
        <a href="/" class="text-2xl font-extrabold text-primary">Podium</a>
        <p class="text-base-content/70 text-sm mt-1">Hackathon peer judging platform</p>
      </div>
      
      <!-- Navigation Menu -->
      <div class="flex-1 p-4">
        <ul class="menu menu-vertical space-y-2">
          {#each Object.entries(navOptions) as [path, label]}
            <li>
              <a 
                href={path} 
                class="flex items-center gap-3 p-3 rounded-lg transition-colors"
                class:bg-primary={page.url.pathname === path}
                class:text-primary-content={page.url.pathname === path}
              >
                <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2H5a2 2 0 00-2-2z" />
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 5a2 2 0 012-2h4a2 2 0 012 2v6a2 2 0 01-2 2H10a2 2 0 01-2-2V5z" />
                </svg>
                <span class="font-medium">{label}</span>
              </a>
            </li>
          {/each}
          
          <!-- Projects Section -->
          <li>
            <button 
              onclick={() => {
                projectsClicked = true;
                projectsExpanded = !projectsExpanded;
                goto('/projects');
              }}
              class="flex items-center gap-3 p-3 rounded-lg transition-colors w-full text-left"
              class:bg-primary={isInSection('/projects') || projectsClicked}
              class:text-primary-content={isInSection('/projects') || projectsClicked}
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
              </svg>
              <span class="font-medium flex-1">Projects</span>
              <svg 
                xmlns="http://www.w3.org/2000/svg" 
                class="h-4 w-4 transition-transform duration-200"
                class:rotate-180={projectsExpanded}
                fill="none" 
                viewBox="0 0 24 24" 
                stroke="currentColor"
              >
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
              </svg>
            </button>
          </li>
          
          <!-- Projects Sub-navigation -->
          {#if projectsExpanded}
            {#each Object.entries(projectSubNav) as [subPath, subLabel]}
              <li class="ml-6">
                <a 
                  href={subPath} 
                  class="flex items-center gap-3 p-2 rounded-lg transition-colors text-sm"
                  class:bg-primary={page.url.pathname === subPath}
                  class:text-primary-content={page.url.pathname === subPath}
                >
                  <span class="w-2 h-2 rounded-full bg-current opacity-50"></span>
                  <span>{subLabel}</span>
                </a>
              </li>
            {/each}
          {/if}
          
          <!-- Events Section -->
          <li>
            <button 
              onclick={() => {
                eventsClicked = true;
                eventsExpanded = !eventsExpanded;
                goto('/events');
              }}
              class="flex items-center gap-3 p-3 rounded-lg transition-colors w-full text-left"
              class:bg-primary={isInSection('/events') || eventsClicked}
              class:text-primary-content={isInSection('/events') || eventsClicked}
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2-2v14a2 2 0 002 2z" />
              </svg>
              <span class="font-medium flex-1">Events</span>
              <svg 
                xmlns="http://www.w3.org/2000/svg" 
                class="h-4 w-4 transition-transform duration-200"
                class:rotate-180={eventsExpanded}
                fill="none" 
                viewBox="0 0 24 24" 
                stroke="currentColor"
              >
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
              </svg>
            </button>
          </li>
          
          <!-- Events Sub-navigation -->
          {#if eventsExpanded}
            {#each Object.entries(eventSubNav) as [subPath, subLabel]}
              <li class="ml-6">
                <a 
                  href={subPath} 
                  class="flex items-center gap-3 p-2 rounded-lg transition-colors text-sm"
                  class:bg-primary={page.url.pathname === subPath}
                  class:text-primary-content={page.url.pathname === subPath}
                >
                  <span class="w-2 h-2 rounded-full bg-current opacity-50"></span>
                  <span>{subLabel}</span>
                </a>
              </li>
            {/each}
          {/if}
        </ul>
      </div>
      
      <!-- Bottom Section -->
      <div class="p-4 border-t border-base-300">
        <div class="hidden lg:block mb-4">
          <ThemeSwitcher />
        </div>
      </div>
    </div>
  </div>
</div>
{:else}
<!-- Login page without sidebar -->
<div class="min-h-screen">
  <div class="navbar bg-base-200">
    <div class="flex-1">
      <a href="/" class="btn btn-ghost text-xl font-extrabold">Podium</a>
    </div>
    <div class="flex-none">
      <ThemeSwitcher />
    </div>
  </div>
  
  <div class="p-6">
    {#if navigating.to && navigating.type != "form"}
      <div class="flex items-center justify-center min-h-screen flex-col">
        <span class="loading loading-ball loading-lg mb-2"></span>
        <p>{loadingText}</p>
      </div>
    {:else}
      {@render children()}
    {/if}
  </div>
</div>
{/if}

<!-- Global Info Button -->
<div class="fixed bottom-4 right-4 z-50">
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

<!-- About Modal -->
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
