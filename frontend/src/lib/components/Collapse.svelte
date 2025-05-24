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
      }, 10);
    }
  });

  function handleFocusIn() {
    isOpen = true;
    console.log("Focus in");
  }

  function handleFocusOut(event: FocusEvent) {
    setTimeout(() => {
      try {
        // If the div does not contain the active element (isn't focused),
        if (!collapseDiv.contains(document.activeElement)) {
          isOpen = false;
        }
      } catch (error) {
        // If we the active element doesn't exist stare into space and ponder why
        // (realistically this is probably because the user is navigating away from the page, so close the collapse)
        isOpen = false;
      }
    }, 10); // Small delay to allow new focus to be set
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
  class="collapse bg-base-200 collapse-arrow max-w-2xl mx-auto {isOpen
    ? 'collapse-open'
    : 'collapse-close'}"
  role="button"
  onfocusin={handleFocusIn}
  onfocusout={handleFocusOut}
  bind:this={collapseDiv}
>
  <div class="collapse-title text-xl font-medium text-center">
    {title}
  </div>
  <!-- <div class="collapse-content" onmousedown={handleFocusIn} role="button"> -->
  <!-- <div class="collapse-content" onfocusin={handleFocusIn} onblur={handleFocusOut} role="button" tabindex="0"> -->
  <div class="collapse-content overflow-x-auto" role="button" tabindex="0">
    {@render children?.()}
  </div>
</div>
