<script lang="ts">
  import AttendEvent from "./AttendEvent.svelte";
  import CreateProject from "./CreateProject.svelte";
  import JoinProject from "./JoinProject.svelte";
  
  import { onMount } from "svelte";
  
  let currentStep = $state("welcome"); // "welcome", "joinEvent", "chooseProject", "createProject", "joinProject", or "complete"
  
  async function startJourney() {
    currentStep = "joinEvent";
  }
  
  function goToProjectChoice() {
    currentStep = "chooseProject";
  }
  
  function goToCreateProject() {
    currentStep = "createProject";
  }
  
  function goToJoinProject() {
    currentStep = "joinProject";
  }
  
  function goToComplete() {
    currentStep = "complete";
  }
  
  // Handle successful event join
  function handleEventJoined() {
    // Auto-progress to project choice after successful event join
    setTimeout(() => {
      currentStep = "chooseProject";
    }, 1000); // Small delay to show success feedback
  }
  
  // Handle successful project creation/joining
  function handleProjectAction() {
    // Auto-progress to completion after successful project action
    setTimeout(() => {
      currentStep = "complete";
    }, 1000); // Small delay to show success feedback
  }
</script>

<div class="max-w-md w-full mx-auto">
  <div class="card bg-base-100 shadow-lg" id="wizard-card">
    <div class="card-body">
      {#if currentStep === "welcome"}
        <!-- Welcome Screen -->
        <div class="text-center py-8">
          <h1 class="text-4xl font-bold text-primary mb-4">Welcome to Podium!</h1>
          <h2 class="text-xl font-semibold text-base-content mb-6">Ready to submit your project for voting?</h2>
          <button 
          class="btn btn-primary btn-lg btn-wide"
          onclick={startJourney}
          >
          Start
          </button>
        </div>
      {:else if currentStep === "joinEvent"}
        <!-- Join Event Step -->
        <div class="mb-4">
          <button 
            class="btn btn-ghost btn-sm"
            onclick={() => currentStep = "welcome"}
          >
            ← Back
          </button>
        </div>
        <h2 class="card-title text-xl mb-4">Join Event (1/3)</h2>
        
        <AttendEvent onEventJoined={handleEventJoined} />
        
        <!-- Continue button after attending event - now optional since auto-progression -->
        <div class="mt-6 text-center">
          <button 
            class="text-base-content/60 hover:text-base-content transition-colors cursor-pointer text-sm underline bg-transparent border-none"
            onclick={goToProjectChoice}
          >
            Click here if you're in an event (and already used this flow) and want to create another project.
          </button>
        </div>
      {:else if currentStep === "chooseProject"}
        <!-- Choose Project Action Step -->
        <div class="mb-4">
          <button 
            class="btn btn-ghost btn-sm"
            onclick={() => currentStep = "joinEvent"}
          >
            ← Back
          </button>
        </div>
        <h2 class="card-title text-xl mb-4">Choose Your Project (2/3)</h2>
        
        <div class="text-center py-6 space-y-6">
          <p class="text-base-content/70 mb-6">
            Do you want to create a new project or join an existing one?
          </p>
          
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
        <h2 class="card-title text-xl mb-4">Create Project (3/3)</h2>
        
        <CreateProject onProjectCreated={handleProjectAction} />
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
        <h2 class="card-title text-xl mb-4">Join Project (3/3)</h2>
        
        <JoinProject onProjectJoined={handleProjectAction} />
      {:else if currentStep === "complete"}
        <!-- Completion Step -->
        <div class="text-center py-8">
          <div class="mb-8">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-16 w-16 text-success mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <h1 class="text-3xl font-bold text-success mb-4">All Set!</h1>
            <p class="text-base-content/70 mb-6">Your project has been submitted and it's under review!</p>

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
      {/if}
    </div>
  </div>
</div>
