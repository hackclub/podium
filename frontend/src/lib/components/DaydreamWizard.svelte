<script lang="ts">
  import DaydreamCreateProject from "./DaydreamCreateProject.svelte";
  import JoinProject from "./JoinProject.svelte";
  
  // Accept list of Daydream events from the parent
  let { daydreams = [] }: { daydreams: any[] } = $props();
  let currentDaydream = daydreams[0];
  console.log(currentDaydream);
  
  let currentStep = $state("chooseProject"); // "chooseProject", "createProject", "joinProject", "validateLoading", "validateSuccess", or "validateFailure"
  let validationState = $state("loading"); // "loading", "success", "failure"
  
  function goToCreateProject() {
    currentStep = "createProject";
  }
  
  function goToJoinProject() {
    currentStep = "joinProject";
  }
  
  function goToValidateProject() {
    validationState = "loading";
    currentStep = "validateProject";

    // TODO: REMOVE THIS WHEN HOOKING STUFF UP
    // ---------------------------------------
    setTimeout(() => validationState = "failure", 0);
  }
  
  function revalidate() {
    validationState = "loading";
  }
  
  // Handle successful project creation/joining
  function handleProjectAction() {
    // Auto-progress to validation after successful project action
    setTimeout(() => {
      goToValidateProject();
    }, 1000); // Small delay to show success feedback
  }
</script>

<div class="max-w-md w-full mx-auto">
  <div class="card bg-base-100 shadow-lg" id="wizard-card">
    <div class="card-body">
      {#if currentStep === "chooseProject"}
        <!-- Choose Project Action Step -->
        <div class="text-center py-8">
          <h1 class="text-4xl font-bold text-primary mb-4">Welcome to Podium!</h1>
          <h2 class="text-lg text-base-content mb-6 px-8">Here's where you can submit your project for <span class="underline">{currentDaydream.name}</span>.</h2>
          
          <div class="grid grid-cols-1 gap-4">
            <button 
              class="btn btn-primary btn-lg"
              onclick={goToCreateProject}
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
              </svg>
              Create New Project
            </button>
            
            <button 
              class="btn btn-outline btn-lg"
              onclick={goToJoinProject}
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
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
            onclick={() => currentStep = "chooseProject"}
          >
            ← Back
          </button>
        </div>
        <h2 class="card-title text-xl">Create Project</h2>
        
        <DaydreamCreateProject onProjectCreated={handleProjectAction} preselectedEvent={currentDaydream} />
      {:else if currentStep === "joinProject"}
        <!-- Join Project Step -->
        <div class="mb-4">
          <button 
            class="btn btn-ghost btn-sm"
            onclick={() => currentStep = "chooseProject"}
          >
            ← Back
          </button>
        </div>
        <h2 class="card-title text-xl mb-4">Join Project</h2>
        
        <JoinProject onProjectJoined={handleProjectAction} />
      {:else if currentStep === "validateProject"}
        <!-- Validate Project Step -->
        {#if validationState === "loading"}
          <!-- Loading State -->
          <div class="text-center py-8">
            <div class="mb-8">
              <div class="loading loading-spinner loading-lg text-primary mx-auto mb-4"></div>
              <h1 class="text-3xl font-bold text-primary mb-4">Validating Project...</h1>
              <p class="text-base-content/70 mb-6">We're running some automated checks on your project to make sure it's published correctly. This shouldn't take long!</p>
            </div>
          </div>
        {:else if validationState === "success"}
          <!-- Success State -->
          <div class="text-center py-8">
            <div class="mb-8">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-16 w-16 text-success mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <h1 class="text-3xl font-bold text-success mb-4">All Set!</h1>
              <p class="text-base-content/70 mb-6">Your project has been submitted successfully, and you can now vote on others' projects!</p>
            </div>
            
            <div class="space-y-3">
              <a href="/projects" class="btn btn-primary btn-lg btn-wide">
                View / Edit Your Projects
              </a>
              <a href="/events" class="btn btn-outline btn-lg btn-wide">
                Events (Voting/Galleries)
              </a>
            </div>
          </div>
        {:else if validationState === "failure"}
          <!-- Failure State -->
          <div class="text-center py-8">
            <div class="mb-8">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-16 w-16 text-[#ff627c] mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
              <h1 class="text-3xl font-bold text-error mb-4">Failed to validate project</h1>
              <p class="text-base-content/70 mb-6">We found an issue with your submission:</p>
              
              <div class="bg-[#ffa1b1]/50 border border-[#97404f]/50 rounded-lg p-4 mb-6 text-left">
                <pre class="font-mono text-sm text-base-content whitespace-pre-wrap">- Your GitHub repository does not contain the game files
- Your itch.io link doesn't have a play button</pre>
              </div>
            </div>
            
              <button 
                class="btn btn-primary btn-lg btn-wide"
                onclick={revalidate}
              >
                Revalidate
              </button>
          </div>
        {/if}
      {/if}
    </div>
  </div>
</div>
