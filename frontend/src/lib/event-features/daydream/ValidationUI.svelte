<script lang="ts">
  import type { ValidationResult } from "../types";
  import type { ProjectPublic } from "$lib/client/types.gen";

  interface Props {
    validation: ValidationResult;
    project: ProjectPublic;
  }

  let { validation, project }: Props = $props();
</script>

<div class="absolute top-2 -right-4 z-20">
  <div
    class="bg-base-100 shadow-lg border border-base-300 rounded-lg p-3 text-sm max-w-56"
  >
    <div class="flex items-center gap-2 mb-2">
      {#if validation.isValid}
        <div class="badge badge-success badge-sm">✓</div>
      {:else}
        <div class="badge badge-error badge-sm">✗</div>
      {/if}
      <span class="font-semibold text-sm">URL Check</span>
    </div>
    <div
      class="text-sm font-medium {validation.isValid
        ? 'text-success'
        : 'text-red-600'} break-words"
    >
      {validation.message}
    </div>
    {#if validation.metadata?.swagEligible}
      <div class="text-sm text-success font-semibold mt-2">
        🎁 Eligible for swag!
      </div>
    {/if}
  </div>
</div>
