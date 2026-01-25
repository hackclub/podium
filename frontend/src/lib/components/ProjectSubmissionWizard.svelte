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
   *
   * URL Hash Tracking:
   * - The wizard step is reflected in the URL hash (e.g., #create, #join)
   * - Browser back/forward navigation works correctly
   * - Invalid hash values are ignored (user cannot break the flow)
   */

  import { onMount, onDestroy } from "svelte";
  import { replaceState } from "$app/navigation";
  import JoinProject from "./JoinProject.svelte";
  import type { ProjectPrivate, EventPrivate } from "$lib/client";
  import { validateProject } from "$lib/validation";
  import CreateProject from "./CreateProject.svelte";
  import UpdateProjectModal from "./UpdateProjectModal.svelte";
  import Modal from "./Modal.svelte";

  type WizardStep =
    | "chooseProject"
    | "createProject"
    | "joinProject"
    | "validateProject"
    | "success";

  // Map URL hash values to wizard steps
  const HASH_TO_STEP: Record<string, WizardStep> = {
    "": "chooseProject",
    "choose": "chooseProject",
    "create": "createProject",
    "join": "joinProject",
    "validate": "validateProject",
    "success": "success",
  };

  // Map wizard steps to URL hash values
  const STEP_TO_HASH: Record<WizardStep, string> = {
    chooseProject: "choose",
    createProject: "create",
    joinProject: "join",
    validateProject: "validate",
    success: "success",
  };

  // Steps that require a project to exist (cannot be accessed directly via URL)
  const PROTECTED_STEPS: Set<WizardStep> = new Set(["validateProject", "success"]);

  interface Props {
    /** The flagship event(s) the user is attending */
    flagshipEvents: EventPrivate[];
    /** User's existing projects */
    projects: ProjectPrivate[];
    /** Custom welcome message (optional) */
    welcomeMessage?: string;
  }

  let { flagshipEvents = [], projects = [], welcomeMessage }: Props = $props();

  let currentEvent = $state(flagshipEvents[0]);
  let validationResult = $state<any>(null); // Store full validation result
  let updateProjectModal: Modal = $state() as Modal;
  let currentStep = $state<WizardStep>("chooseProject");
  let validationState = $state<"loading" | "success" | "failure">("loading");
  let isInitialized = $state(false);
  let hasAutoValidated = $state(false);

  // Check if user already has a project for this event
  const hasExistingProject = $derived(() => {
    if (!currentEvent || !projects.length) return false;
    return projects.some((project) => project.event_id === currentEvent.id);
  });

  // Get user's project for the current event (prioritize owned projects)
  const eventProjects = $derived(() => {
    return projects.filter((p) => p.event_id === currentEvent.id);
  });

  const userProject = $derived(() => {
    const allProjects = eventProjects();
    // Just return the most recent project (last in the array, assuming chronological order)
    return allProjects[allProjects.length - 1];
  });

  const hasMultipleProjects = $derived(() => eventProjects().length > 1);

  /**
   * Validates if a step transition is allowed based on current state.
   * Prevents users from accessing protected steps via URL manipulation.
   */
  function isStepAllowed(step: WizardStep): boolean {
    // Protected steps require an existing project
    if (PROTECTED_STEPS.has(step)) {
      return hasExistingProject();
    }
    return true;
  }

  /**
   * Updates the URL hash to reflect the current step.
   * Uses replaceState to avoid polluting browser history with every step change.
   */
  function updateHash(step: WizardStep) {
    const hash = STEP_TO_HASH[step];
    const newUrl = new URL(window.location.href);
    newUrl.hash = hash;
    replaceState(newUrl, {});
  }

  /**
   * Reads the current URL hash and returns the corresponding step,
   * falling back to chooseProject if invalid or not allowed.
   */
  function getStepFromHash(): WizardStep {
    const hash = window.location.hash.replace("#", "");
    const step = HASH_TO_STEP[hash];
    
    if (step && isStepAllowed(step)) {
      return step;
    }
    
    // Default: if user has project, go to validate; otherwise choose
    return hasExistingProject() ? "validateProject" : "chooseProject";
  }

  /**
   * Handle browser back/forward navigation
   */
  function handlePopState() {
    const step = getStepFromHash();
    if (step !== currentStep) {
      setStep(step, false); // Don't update hash again
    }
  }

  /**
   * Sets the current step and optionally updates the URL hash.
   */
  function setStep(step: WizardStep, updateUrl = true) {
    if (!isStepAllowed(step)) {
      step = hasExistingProject() ? "validateProject" : "chooseProject";
    }
    currentStep = step;
    if (updateUrl && typeof window !== "undefined") {
      updateHash(step);
    }
  }

  // Initialize from URL hash on mount
  onMount(() => {
    window.addEventListener("popstate", handlePopState);
    
    // Only read from hash if user doesn't have an existing project
    // (if they do, the $effect below will handle it)
    if (!hasExistingProject()) {
      const initialStep = getStepFromHash();
      setStep(initialStep);
    }
    isInitialized = true;
  });

  onDestroy(() => {
    if (typeof window !== "undefined") {
      window.removeEventListener("popstate", handlePopState);
    }
  });

  // Update step when data is available (user has existing project) - run once
  $effect(() => {
    if (hasExistingProject() && isInitialized && !hasAutoValidated) {
      hasAutoValidated = true;
      goToValidateProject();
    }
  });

  // Sync URL hash when step changes programmatically
  $effect(() => {
    if (isInitialized && typeof window !== "undefined") {
      const currentHash = window.location.hash.replace("#", "");
      const expectedHash = STEP_TO_HASH[currentStep];
      if (currentHash !== expectedHash) {
        updateHash(currentStep);
      }
    }
  });

  function goToCreateProject() {
    setStep("createProject");
  }

  function goToJoinProject() {
    setStep("joinProject");
  }

  async function goToValidateProject() {
    validationState = "loading";
    setStep("validateProject");

    const project = userProject();
    if (project) {
      const result = await validateProject(project.id);
      validationResult = result;
      validationState = result.valid ? "success" : "failure";
    } else {
      validationState = "success";
    }
  }

  function handleProjectAction() {
    goToValidateProject();
  }

  function submitAnotherProject() {
    setStep("chooseProject");
    validationState = "loading";
  }

  function goBack() {
    setStep("chooseProject");
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
          <button class="btn btn-ghost btn-sm" onclick={goBack}>
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
          <button class="btn btn-ghost btn-sm" onclick={goBack}>
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
  <UpdateProjectModal preselectedProject={userProject()!} events={flagshipEvents} bind:modal={updateProjectModal} onProjectUpdated={goToValidateProject} />
{/if}
