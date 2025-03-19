<script lang="ts">
  import ProjectCard from "$lib/components/ProjectCard.svelte";
  import type { PageData } from "./$types";
  import Icon from "@iconify/svelte";
  import { derived, writable } from 'svelte/store';

  let eventId: string;
  let { data }: { data: PageData } = $props();
  let { projects, event } = data;
  
  // Sort projects by points in descending order
  let sortedProjects = [...projects].sort((a, b) => {
    const pointsA = a.points || 0;
    const pointsB = b.points || 0;
    return pointsB - pointsA;
  });
  
  // Function to determine rank badge style based on position
  function getRankStyle(index: number): string {
    if (index === 0) return "bg-yellow-500 text-black"; // Gold
    if (index === 1) return "bg-gray-300 text-black";   // Silver
    if (index === 2) return "bg-amber-600 text-white";  // Bronze
    return "bg-neutral-focus";                          // Others
  }
</script>

<div class="max-w-6xl mx-auto py-8 px-6">
  <header class="mb-8 text-center">
    <h1 class="text-3xl font-medium mb-3">Leaderboard</h1>
    <p class="text-lg opacity-80 max-w-2xl mx-auto">
      Results for {event.name}
    </p>
  </header>

  <!-- Top 3 Winners Podium (if there are at least 3 projects) -->
  {#if sortedProjects.length >= 3}
    <div class="mb-12">
      <h2 class="text-xl font-medium mb-6 text-center">Top Projects</h2>
      <div class="flex flex-col md:flex-row justify-center items-end gap-4 max-w-4xl mx-auto">
        <!-- Second Place -->
        <div class="order-2 md:order-1 flex-1 text-center">
          <div class="bg-gray-300 text-black rounded-t-lg py-2 px-4 inline-block mb-2">
            <Icon icon="mdi:numeric-2-circle" style="font-size: 24px;" class="mr-1" />
            2nd Place
          </div>
          <div class="h-32 md:h-40 bg-neutral flex items-center justify-center p-4 rounded-lg">
            <div class="text-center">
              <p class="font-bold text-lg">{sortedProjects[1].name}</p>
              <p class="text-accent text-xl font-bold mt-2">{sortedProjects[1].points} points</p>
            </div>
          </div>
        </div>
        
        <!-- First Place (taller) -->
        <div class="order-1 md:order-2 flex-1 text-center">
          <div class="bg-yellow-500 text-black rounded-t-lg py-2 px-4 inline-block mb-2">
            <Icon icon="mdi:trophy" style="font-size: 24px;" class="mr-1" />
            1st Place
          </div>
          <div class="h-40 md:h-52 bg-neutral flex items-center justify-center p-4 rounded-lg border-2 border-yellow-500">
            <div class="text-center">
              <p class="font-bold text-xl">{sortedProjects[0].name}</p>
              <p class="text-accent text-2xl font-bold mt-2">{sortedProjects[0].points} points</p>
            </div>
          </div>
        </div>
        
        <!-- Third Place -->
        <div class="order-3 flex-1 text-center">
          <div class="bg-amber-600 text-white rounded-t-lg py-2 px-4 inline-block mb-2">
            <Icon icon="mdi:numeric-3-circle" style="font-size: 24px;" class="mr-1" />
            3rd Place
          </div>
          <div class="h-24 md:h-32 bg-neutral flex items-center justify-center p-4 rounded-lg">
            <div class="text-center">
              <p class="font-bold text-lg">{sortedProjects[2].name}</p>
              <p class="text-accent text-xl font-bold mt-2">{sortedProjects[2].points} points</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  {/if}

  <!-- Full Rankings Table -->
  <div class="bg-neutral p-6 rounded-lg mb-8 border border-accent/20">
    <h2 class="text-xl font-medium mb-6">Complete Rankings</h2>
    
    <div class="overflow-x-auto">
      <table class="table w-full">
        <thead>
          <tr>
            <th class="text-base">Rank</th>
            <th class="text-base">Project</th>
            <th class="text-base">Points</th>
            <th class="text-base">Links</th>
          </tr>
        </thead>
        <tbody>
          {#each sortedProjects as project, index}
            <tr class="hover">
              <td>
                <div class={`badge ${getRankStyle(index)} badge-lg`}>{index + 1}</div>
              </td>
              <td class="font-medium">{project.name}</td>
              <td class="font-bold text-accent">{project.points}</td>
              <td>
                <div class="flex gap-2">
                  <a href={project.repo} target="_blank" rel="noopener" class="btn btn-sm btn-outline">
                    <Icon icon="mdi:github" style="font-size: 18px;" />
                    Repo
                  </a>
                  <a href={project.demo} target="_blank" rel="noopener" class="btn btn-sm btn-outline">
                    <Icon icon="mdi:web" style="font-size: 18px;" />
                    Demo
                  </a>
                </div>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  </div>
  
  <div class="mt-8 text-center">
    <a href={`/events/${event.id}`} class="btn btn-outline">
      <Icon icon="mdi:arrow-left" style="font-size: 20px;" class="mr-2" />
      Back to Event
    </a>
  </div>
</div>
