<script lang="ts">
  import { themes } from "$lib/consts";
  import { setSystemTheme } from "$lib/misc";
</script>

<div class="dropdown dropdown-top" id="theme-switcher">
  <div tabindex="0" role="button" class="btn m-1">
    Theme
    <svg
      width="12px"
      height="12px"
      class="inline-block h-2 w-2 fill-current opacity-60"
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 384 512"
    >
      <!--!Font Awesome Free 6.7.2 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license/free Copyright 2024 Fonticons, Inc.--><path
        d="M214.6 41.4c-12.5-12.5-32.8-12.5-45.3 0l-160 160c-12.5 12.5-12.5 32.8 0 45.3s32.8 12.5 45.3 0L160 141.2 160 448c0 17.7 14.3 32 32 32s32-14.3 32-32l0-306.7L329.4 246.6c12.5 12.5 32.8 12.5 45.3 0s12.5-32.8 0-45.3l-160-160z"
      /></svg
    >
  </div>
  <ul
    tabindex="0"
    class="dropdown-content bg-base-300 rounded-box z-1 w-52 p-1 shadow-2xl overflow-auto max-h-52 mr-0"
    role="menu"
  >
    <!-- Option to respect system theme by removing the theme from localStorage -->
    <li>
      <input
        type="radio"
        name="theme-dropdown"
        class="theme-controller btn btn-sm btn-block btn-ghost justify-start"
        aria-label="system"
        onchange={() => {
          localStorage.removeItem("theme");
          setSystemTheme();
        }}
      />
    </li>
    {#each themes as theme}
      <li>
        <input
          type="radio"
          name="theme-dropdown"
          class="theme-controller btn btn-sm btn-block btn-ghost justify-start"
          value={theme}
          aria-label={theme}
          data-set-theme={theme}
          data-act-class="ACTIVECLASS"
        />
      </li>
    {/each}
  </ul>
</div>
