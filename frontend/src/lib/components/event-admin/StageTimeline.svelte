<script lang="ts">
  import { untrack } from "svelte";
  import { EventsService } from "$lib/client/sdk.gen";
  import type { EventPrivate } from "$lib/client/types.gen";
  import { handleError } from "$lib/misc";
  import { toast } from "svelte-sonner";

  interface Props {
    event: EventPrivate;
    onUpdate?: (updated: EventPrivate) => void;
  }

  let { event, onUpdate }: Props = $props();

  // Local mirror so clicking a stage updates the timeline immediately even if
  // the parent doesn't reassign the `event` prop.
  let phase = $state(untrack(() => event.phase));
  $effect(() => {
    phase = event.phase;
  });

  // Keep in sync with backend EventPhase enum (backend/podium/constants.py)
  const stages = [
    { id: "draft", label: "Draft", description: "Hidden — not yet accepting submissions" },
    { id: "submission", label: "Submission", description: "Open for project submissions" },
    { id: "voting", label: "Voting", description: "Submissions closed, voting is open" },
    { id: "closed", label: "Closed", description: "Voting closed, leaderboard visible" },
  ] as const;

  let saving = $state(false);

  const currentIndex = $derived(
    Math.max(0, stages.findIndex((s) => s.id === phase)),
  );

  async function setPhase(next: string) {
    if (saving || next === phase) return;
    saving = true;
    const { data, error } =
      await EventsService.updateEventAdminEventsAdminEventIdPatch({
        path: { event_id: event.id },
        body: { phase: next },
        throwOnError: false,
      });
    if (error) {
      handleError(error);
    } else if (data) {
      phase = data.phase;
      onUpdate?.(data);
      toast.success(`Event set to ${next}`);
    }
    saving = false;
  }
</script>

<div class="card bg-base-200">
  <div class="card-body gap-4">
    <h3 class="card-title text-base">Event Status</h3>

    <!-- DaisyUI `steps` renders the dot-and-connector timeline. Each <li> is
         the click target so the dot AND the label are both hit areas. -->
    <ul class="steps steps-vertical sm:steps-horizontal w-full">
      {#each stages as stage, i}
        <li
          class="step {i <= currentIndex ? 'step-primary' : ''}"
          data-content={i < currentIndex ? "✓" : i + 1}
        >
          <button
            type="button"
            class="link link-hover font-medium disabled:opacity-60 disabled:no-underline"
            disabled={saving}
            onclick={() => setPhase(stage.id)}
          >
            {stage.label}
          </button>
        </li>
      {/each}
    </ul>

    <div class="flex flex-wrap items-center justify-between gap-2">
      <p class="text-sm text-base-content/70">
        {stages[currentIndex].description}
      </p>
      <!-- Explicit select as a second, unambiguous control. Useful on mobile
           and for users who don't realize the timeline is clickable. -->
      <label class="flex items-center gap-2 text-sm">
        <span class="text-base-content/70">Set stage:</span>
        <select
          class="select select-sm select-bordered"
          disabled={saving}
          value={phase}
          onchange={(e) => setPhase((e.currentTarget as HTMLSelectElement).value)}
        >
          {#each stages as stage}
            <option value={stage.id}>{stage.label}</option>
          {/each}
        </select>
      </label>
    </div>
  </div>
</div>
