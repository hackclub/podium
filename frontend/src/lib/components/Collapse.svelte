<script lang="ts">
  import { onMount, type Snippet } from "svelte";

  let {
    title,
    children,
    expandByDefault = false,
  }: { title: string; children: Snippet; expandByDefault?: boolean } = $props();

  let collapseDiv: HTMLDivElement;

  let isOpen = $state(false);

  onMount(() => {
    // If expandByDefault is true, focus the collapseDiv to open it
    if (expandByDefault) {
      setTimeout(() => {
        collapseDiv.focus();
        isOpen = true;
      }, 10);
    }
  });

  function handleFocusIn() {
    isOpen = true;
  }

  function handleFocusOut(event: FocusEvent) {
    setTimeout(() => {
      try {
        // If the div does not contain the active element (isn't focused),
        if (!collapseDiv.contains(document.activeElement)) {
          isOpen = false;
        }
      } catch (error) {
        // If the active element doesn't exist, close the collapse
        // (realistically this is probably because the user is navigating away from the page)
        isOpen = false;
      }
    }, 10); // Small delay to allow new focus to be set
  }
  
  function toggleCollapse() {
    isOpen = !isOpen;
    if (isOpen) {
      collapseDiv.focus();
    }
  }
  
  function handleKeyDown(e: KeyboardEvent) {
    if (e.key === 'Enter') {
      toggleCollapse();
    }
  }
</script>

<!-- <div class="collapse bg-base-200 text-center collapse-arrow max-w-2xl mx-auto">
    <input type="checkbox" />
    <div class="collapse-title text-xl font-medium">{title}</div>
    <div class="collapse-content">
      {@render children?.()}
    </div>
  </div> -->

<div
  tabindex="0"
  class="collapse collapse-arrow rounded-lg transition-all duration-300 max-w-3xl mx-auto {isOpen
    ? 'collapse-open'
    : 'collapse-close'}"
  role="button"
  onfocusin={handleFocusIn}
  onfocusout={handleFocusOut}
  bind:this={collapseDiv}
>
  <div 
    class="collapse-title text-xl font-medium text-center py-4 flex items-center justify-between cursor-pointer"
    onclick={toggleCollapse}
    onkeydown={handleKeyDown}
  >
    <span class="flex-grow text-center">{title}</span>
  </div>
  
  <div class="collapse-content p-4 overflow-x-auto" role="region">
    <div class="pt-2">
      {@render children?.()}
    </div>
  </div>
</div>

<style>
  .collapse {
    @apply bg-transparent border-t border-accent/10;
  }
  
  .collapse-open .collapse-title {
    @apply text-accent;
  }
</style>
