<script lang="ts">
  import { toast } from "svelte-sonner";
  import { handleError, invalidateProjects } from "$lib/misc";

  import { ProjectsService } from "$lib/client";
  import type { JoinProjectProjectsJoinPostData } from "$lib/client";
  import { afterNavigate, goto } from "$app/navigation";
  import { onMount } from "svelte";

  let toSend: JoinProjectProjectsJoinPostData = $state({
    query: { join_code: "" },
  });

  async function joinProject() {
    try {
      await ProjectsService.joinProjectProjectsJoinPost({
        ...toSend,
        throwOnError: true,
      });
      toast("Joined project successfully");
      invalidateProjects();
      // Reset
      toSend.query.join_code = "";
    } catch (err) {
      handleError(err);
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
      class="w-full input input-bordered"
    />
    <button class="btn-block btn btn-primary" onclick={joinProject}>
      Join the development of something great!
    </button>
  </div>
  <!-- </form> -->
</div>
