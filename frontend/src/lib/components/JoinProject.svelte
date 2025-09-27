<script lang="ts">
  import { toast } from "svelte-sonner";
  import { customInvalidateAll, handleError } from "$lib/misc";

  import { ProjectsService } from "$lib/client";
  import type { JoinProjectProjectsJoinPostData } from "$lib/client";
  import { afterNavigate, goto } from "$app/navigation";
  import { onMount } from "svelte";

  // Accept callback prop for when project is successfully joined
  let { onProjectJoined }: { onProjectJoined?: () => void } = $props();

  let toSend: JoinProjectProjectsJoinPostData = $state({
    query: { join_code: "" },
  });

  async function joinProject() {
    const { error: err } = await ProjectsService.joinProjectProjectsJoinPost({
      ...toSend,
      throwOnError: false,
    });
    if (err) {
      handleError(err);
      return;
    }
    toast.success("Joined project successfully");
    await customInvalidateAll();
    // Reset
    toSend.query.join_code = "";

    // Call the callback if provided (for auto-progression in SignupWizard)
    if (onProjectJoined) {
      onProjectJoined();
    }
  }

  onMount(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const join_code = urlParams.get("join_code");
    if (join_code) {
      toSend.query.join_code = join_code;
      joinProject();
      // Clear the query param
      const url = new URL(window.location.href);
      url.searchParams.delete("join_code");
      goto(url.toString(), { replaceState: true, noScroll: true });
    }
  });
</script>

<div class="p-4 max-w-md mx-auto">
  <!-- <form onsubmit={joinProject} class="space-y-4"> -->
  <div class="space-y-4">
    <label class="label" for="join_code">Join Code</label>
    <input
      id="join_code"
      type="text"
      bind:value={toSend.query.join_code}
      placeholder="~4 character case-insensitive join code"
      class="input input-bordered w-full"
    />
    <button class="btn-block btn btn-primary" onclick={joinProject}>
      Join the development of something great!
    </button>
  </div>
  <!-- </form> -->
</div>
