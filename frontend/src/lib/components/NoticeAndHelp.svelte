<script lang="ts">
  import { onMount } from "svelte";
  import Modal from "./Modal.svelte";
  
  let noticeVisible = $state(true);
  let helpModal: Modal = $state() as Modal;
  
  onMount(() => {
    // Check localStorage for notice preference
    const noticeHidden = localStorage.getItem('podium-notice-hidden');
    if (noticeHidden === 'true') {
      noticeVisible = false;
    }
  });
  
  function dismissNotice() {
    noticeVisible = false;
    localStorage.setItem('podium-notice-hidden', 'true');
  }
  
  function showHelp() {
    helpModal.openModal();
  }
</script>

<!-- Dismissible Notice -->
{#if noticeVisible}
  <div class="bg-info text-center rounded-xl max-w-2xl mx-auto mb-6 p-4 relative" id="help-notice">
    <button
      onclick={dismissNotice}
      class="btn btn-sm btn-circle btn-ghost absolute top-2 right-2"
      aria-label="Dismiss notice"
    >
      <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
      </svg>
    </button>
    <p class="text-info-content pr-8">
      If Podium isn't working and you need urgent help, DM @Angad Behl on Slack or call +1 (415) 570-4995.
    </p>
  </div>
{/if}

<!-- Help Button -->
<div class="fixed bottom-4 right-4 z-50">
  <button
    class="btn btn-info btn-square btn-md font-serif font-light"
    aria-label="Help"
    onclick={showHelp}
  >
    ?
  </button>
</div>

<!-- Help Modal -->
<Modal bind:this={helpModal} title="About Podium">
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
  <p class="py-2">
    <strong>Urgent Help:</strong> If Podium isn't working and you need immediate assistance, 
    DM @Angad Behl on Slack or call <a href="tel:+14155704995" class="hover-link">+1 (415) 570-4995</a>.
  </p>
  <p class="text-right">
    <a href="https://github.com/slashtechno" class="hover-link"
      >-Angad Behl</a
    >
  </p>
</Modal>
