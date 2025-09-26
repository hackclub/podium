<script lang="ts">
  import { EventsService } from "$lib/client/sdk.gen";
  import { toast } from "svelte-sonner";
  import { customInvalidateAll, handleError } from "$lib/misc";
  import type { AttendEventEventsAttendPostData } from "$lib/client";
  import { afterNavigate, goto, invalidate } from "$app/navigation";
  import { onMount } from "svelte";
  
  // Accept callback prop for when event is successfully joined
  let { onEventJoined }: { onEventJoined?: () => void } = $props();
  
  let toSend: AttendEventEventsAttendPostData = $state({
    query: { join_code: "", referral: "" },
  });

  async function attendEvent() {
    const { error: err } = await EventsService.attendEventEventsAttendPost({
      ...toSend,
      throwOnError: false,
    });
    if (err) {
      handleError(err);
      return;
    }
    toast.success("Joined event successfully");
    await customInvalidateAll();
    // Reset
    toSend.query.join_code = "";
    toSend.query.referral = "";
    
    // Call the callback if provided (for auto-progression in SignupWizard)
    if (onEventJoined) {
      onEventJoined();
    }
  }

  onMount(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const join_code = urlParams.get("join_code");
    if (join_code) {
      toSend.query.join_code = join_code;
      toSend.query.referral = urlParams.get("referral") ?? "Joined from link";
      attendEvent();
      // Clear the query param
      // TODO: import { page } from "$app/state"; page.url
      const url = new URL(window.location.href);
      url.searchParams.delete("join_code");
      goto(url.toString(), { replaceState: true, noScroll: true });
    }
  });
</script>

<div class="w-full">
  <!-- <form onsubmit={attendEvent} class="space-y-4"> -->
  <div class="space-y-4">
    <fieldset class="fieldset">
      <!-- legend removed -->

      <label class="label" for="join_code">Join Code</label>
      <input
        id="join_code"
        type="text"
        bind:value={toSend.query.join_code}
        placeholder="~4 character case-insensitive join code"
        class="input input-bordered w-full"
      />

      <label class="label" for="referral">
        <span>How did you hear about this event?</span>
        <span class="text-sm">Optional</span>
      </label>
      <input
        id="referral"
        type="text"
        class="input input-bordered w-full"
        placeholder="Friend, social media, etc."
        bind:value={toSend.query.referral}
      />

      <button class="btn-block btn btn-primary" onclick={attendEvent}>
        Join the event!
      </button>
    </fieldset>
  </div>
  <!-- </form> -->
</div>
