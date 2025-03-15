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
  <form onsubmit={joinProject} class="space-y-4">
    <label class="form-control">
      <div class="label">Join Code</div>
      <input
        type="text"
        minlength="4"
        maxlength="4"
        bind:value={toSend.query.join_code}
        placeholder="~4 character case-insensitive join code"
        class="w-full input input-bordered"
      />
    </label>
    <button type="submit" class="btn-block btn btn-primary">
      Join the development of something great!
    </button>
  </form>
</div>
