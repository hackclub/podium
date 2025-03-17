<script lang="ts">
  import { themes } from "$lib/consts";
  import { setSystemTheme } from "$lib/misc";
  import Icon from "@iconify/svelte";
</script>

<div class="dropdown dropdown-top">
  <div tabindex="0" role="button" class="btn btn-circle btn-md shadow-lg">
    <Icon icon="mdi:theme" style="font-size: 24px;"/>
  </div>
  
  <ul
    tabindex="0"
    class="dropdown-content bg-base-300 rounded-box z-50 w-40 p-2 shadow-2xl overflow-auto max-h-80 mt-2"
    role="menu"
  >
    <li class="mb-1">
      <button
        class="theme-controller btn btn-sm btn-block justify-start font-medium"
        aria-label="System Theme"
        onclick={() => {
          localStorage.removeItem("theme");
          setSystemTheme();
        }}
      >
        System
      </button>
    </li>
    
    <div class="divider my-1"></div>
    
    {#each themes as theme}
      <li class="mb-1">
        <button
          class="theme-controller btn btn-sm btn-block justify-start font-medium"
          data-set-theme={theme}
          data-act-class="active"
          aria-label={theme}
        >
          <span class="capitalize">{theme}</span>
        </button>
      </li>
    {/each}
  </ul>
</div>

<style>
  .theme-controller.active {
    @apply bg-primary text-primary-content;
  }
</style>