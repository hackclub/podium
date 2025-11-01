<script lang="ts">
  /**
   * Generic Flagship Event Wizard
   *
   * A reusable wizard for flagship events that guides users through:
   * 1. Creating or joining a project
   * 2. Validating their submission (if feature provides validator)
   * 3. Navigating to voting/galleries
   *
   * Replaces event-specific wizards like DaydreamWizard with a generic version.
   */

  import JoinProject from "./JoinProject.svelte";
  import type { PrivateProject, PrivateEvent } from "$lib/client";
  import { getEventFeature } from "$lib/event-features/registry";
  import CreateProject from "./CreateProject.svelte";
  import UpdateProjectModal from "./UpdateProjectModal.svelte";
  import Modal from "./Modal.svelte";

  interface Props {
    /** The flagship event(s) the user is attending */
    flagshipEvents: PrivateEvent[];
    /** User's existing projects */
    projects: PrivateProject[];
    /** Custom welcome message (optional) */
    welcomeMessage?: string;
  }

  let { flagshipEvents = [], projects = [], welcomeMessage }: Props = $props();

  let currentEvent = $state(flagshipEvents[0]);
  let validationResult = $state<any>(null); // Store full validation result
  let updateProjectModal: Modal = $state() as Modal;
  let currentStep = $state<
    | "chooseProject"
    | "createProject"
    | "joinProject"
    | "validateProject"
    | "success"
  >("chooseProject");
  let validationState = $state<"loading" | "success" | "failure">("loading");

  // Get the event feature for validation if available
  const eventFeature = $derived(
    currentEvent?.feature_flags_list?.[0]
      ? getEventFeature(currentEvent.feature_flags_list[0])
      : undefined,
  );

  // Check if user already has a project for this event
  const hasExistingProject = $derived(() => {
    if (!currentEvent || !projects.length) return false;
    return projects.some((project) => project.event[0] === currentEvent.id);
  });

  // Get user's project for the current event (prioritize owned projects)
  const eventProjects = $derived(() => {
    return projects.filter((p) => p.event[0] === currentEvent.id);
  });

  const userProject = $derived(() => {
    const allProjects = eventProjects();
    // Just return the most recent project (last in the array, assuming chronological order)
    return allProjects[allProjects.length - 1];
  });

  const hasMultipleProjects = $derived(() => eventProjects().length > 1);

  // Auto-validate when project data changes (after edit/update)
  let lastValidatedProject = $state<string | null>(null);
  $effect(() => {
    const project = userProject();
    if (project && eventFeature?.validateProject && currentStep === "validateProject") {
      // Create a hash of the relevant project fields to detect actual changes
      const projectHash = JSON.stringify({
        repo: project.repo,
        demo: project.demo,
        name: project.name,
        description: project.description,
      });
      
      if (lastValidatedProject !== projectHash) {
        lastValidatedProject = projectHash;
        goToValidateProject();
      }
    }
  });

  // Update step when data is available
  $effect(() => {
    if (hasExistingProject()) {
      // If we have a project, validate it if needed, otherwise show success
      if (eventFeature?.validateProject) {
        goToValidateProject();
      } else {
        currentStep = "success";
      }
    }
  });

  function goToCreateProject() {
    currentStep = "createProject";
  }

  function goToJoinProject() {
    currentStep = "joinProject";
  }

  async function goToValidateProject() {
    validationState = "loading";
    currentStep = "validateProject";

    // Run validation if the feature provides a validator
    if (eventFeature?.validateProject) {
      const project = userProject();
      if (project) {
        const result = await Promise.resolve(eventFeature.validateProject(project));
        validationResult = result; // Store full result including message
        validationState = result.isValid ? "success" : "failure";
      } else {
        validationState = "success"; // No project to validate
      }
    } else {
      // No validator, just succeed
      validationState = "success";
    }
  }

  function handleProjectAction() {
    // Auto-progress to validation/success after project creation/join
    if (eventFeature?.validateProject) {
      goToValidateProject();
    } else {
      currentStep = "success";
    }
  }

  function submitAnotherProject() {
    currentStep = "chooseProject";
    validationState = "loading";
  }
</script>

{#snippet successScreen()}
  <div class="text-center py-8">
    <div class="mb-8">
      <svg
        xmlns="http://www.w3.org/2000/svg"
        class="h-16 w-16 text-success mx-auto mb-4"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
        />
      </svg>
      <h1 class="text-3xl font-bold text-success mb-4">All Set!</h1>
      <p class="text-base-content/70 mb-6">
        {#if hasExistingProject()}
          Your project "<span class="font-semibold">{userProject()?.name}</span>" for
          <span class="underline">{currentEvent.name}</span> passed validation!
        {:else}
          Your project has been submitted successfully! You can now vote
          on others' projects.
        {/if}
      </p>
      {#if hasMultipleProjects()}
        <div class="alert alert-info mb-4">
          <span>You have {eventProjects().length} projects for this event. Make sure to check all of them on the <a href="/projects" class="link">Projects page</a>.</span>
        </div>
      {/if}
    </div>

    <div class="space-y-3">
      <a href="/projects" class="btn btn-primary btn-lg btn-wide">
        View / Edit Your Projects
      </a>
      <a href="/events/{currentEvent.slug}" class="btn btn-outline btn-lg btn-wide">
        Events (Voting/Galleries)
      </a>
      {#if hasExistingProject()}
        <button
          class="btn btn-ghost btn-sm text-base-content/60 hover:text-base-content"
          onclick={submitAnotherProject}
        >
          Submit Another Project
        </button>
      {/if}
    </div>
  </div>
{/snippet}

<div class="max-w-md w-full mx-auto">
  <div class="card bg-base-100 shadow-lg">
    <div class="card-body">
      {#if currentStep === "chooseProject"}
        <!-- Choose Project Action Step -->
        <div class="text-center py-8">
          <h1 class="text-4xl font-bold text-primary mb-4">
            Welcome to Podium!
          </h1>
          <h2 class="text-lg text-base-content mb-6 px-8">
            {#if welcomeMessage}
              {welcomeMessage}
              <span class="underline">{currentEvent.name}</span>.
            {:else}
              Submit your project for
              <span class="underline">{currentEvent.name}</span>.
            {/if}
          </h2>

          <div class="grid grid-cols-1 gap-4">
            <button class="btn btn-primary btn-lg" onclick={goToCreateProject}>
              <svg
                xmlns="http://www.w3.org/2000/svg"
                class="h-6 w-6 mr-2"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M12 4v16m8-8H4"
                />
              </svg>
              Create New Project
            </button>

            <button class="btn btn-outline btn-lg" onclick={goToJoinProject}>
              <svg
                xmlns="http://www.w3.org/2000/svg"
                class="h-6 w-6 mr-2"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"
                />
              </svg>
              Join Existing Project
            </button>
          </div>
        </div>
      {:else if currentStep === "createProject"}
        <!-- Create Project Step -->
        <div class="mb-4">
          <button
            class="btn btn-ghost btn-sm"
            onclick={() => (currentStep = "chooseProject")}
          >
            ← Back
          </button>
        </div>
        <h2 class="card-title text-xl">Create Project</h2>

        <CreateProject
          onProjectCreated={handleProjectAction}
          preselectedEvent={currentEvent}
        />
      {:else if currentStep === "joinProject"}
        <!-- Join Project Step -->
        <div class="mb-4">
          <button
            class="btn btn-ghost btn-sm"
            onclick={() => (currentStep = "chooseProject")}
          >
            ← Back
          </button>
        </div>
        <h2 class="card-title text-xl mb-4">Join Project</h2>

        <JoinProject onProjectJoined={handleProjectAction} />
      {:else if currentStep === "validateProject"}
        <!-- Validate Project Step -->
        {#if validationState === "loading"}
          <div class="text-center py-8">
            <div class="mb-8">
              <div
                class="loading loading-spinner loading-lg text-primary mx-auto mb-4"
              ></div>
              <h1 class="text-3xl font-bold text-primary mb-4">
                Validating Project...
              </h1>
              <p class="text-base-content/70 mb-6">
                Checking your submission against event requirements...
              </p>
            </div>
          </div>
        {:else if validationState === "success"}
          {@render successScreen()}
        {:else if validationState === "failure"}
          <div class="text-center py-8">
            <div class="mb-8">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                class="h-16 w-16 text-error mx-auto mb-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
              <h1 class="text-3xl font-bold text-error mb-4">
                Validation Issues
              </h1>
              <p class="text-base-content/70 mb-2">
                Project: "<span class="font-semibold">{userProject()?.name}</span>"
              </p>
              {#if validationResult?.message}
                <div class="alert alert-error mb-6">
                  <span>{validationResult.message}</span>
                </div>
              {:else}
                <p class="text-base-content/70 mb-6">
                  Your project needs some adjustments. Please fix the issues and
                  try again.
                </p>
              {/if}
              {#if hasMultipleProjects()}
                <div class="alert alert-warning mb-4">
                  <span>You have {eventProjects().length} projects for this event. Check all of them on the <a href="/projects" class="link">Projects page</a>.</span>
                </div>
              {/if}
            </div>

            <div class="space-y-3">
              <button
                class="btn btn-primary btn-lg btn-wide"
                onclick={() => updateProjectModal?.openModal()}
              >
                Edit Your Project
              </button>
            </div>
          </div>
        {/if}
      {:else if currentStep === "success"}
        <!-- Final Success State (no validation) -->
        {@render successScreen()}
      {/if}
    </div>
  </div>
</div>

{#if userProject()}
  <UpdateProjectModal preselectedProject={userProject()!} events={flagshipEvents} bind:modal={updateProjectModal} />
{/if}
