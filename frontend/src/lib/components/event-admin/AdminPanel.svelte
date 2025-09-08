<script lang="ts">
  import { onMount } from 'svelte';
  import { EventsService } from '$lib/client/sdk.gen';
  import type { UserAttendee, Project, Event, Vote, Referral } from '$lib/client/types.gen';
  import LoadingSpinner from '$lib/components/LoadingSpinner.svelte';
  import UpdateEvent from './UpdateEvent.svelte';
  import AttendeesTable from './AttendeesTable.svelte';
  import AdminLeaderboard from './AdminLeaderboard.svelte';
  import VotesTable from './VotesTable.svelte';
  import ReferralsTable from './ReferralsTable.svelte';
  import { handleError, returnLoadingText } from '$lib/misc';
  import { getAuthenticatedUser } from '$lib/user.svelte';
  import { toast } from 'svelte-sonner';

  interface Props {
    event: Event & { owned: boolean; partOfEvent: boolean; join_code?: string };
  }

  let { event }: Props = $props();
  
  // Admin state
  let attendees = $state<UserAttendee[]>([]);
  let adminLeaderboard = $state<Project[]>([]);
  let votes = $state<Vote[]>([]);
  let referrals = $state<Referral[]>([]);
  let loading = $state(false);
  
  // Lookup maps for efficient data access
  let userLookup = $state<Map<string, string>>(new Map());
  let projectLookup = $state<Map<string, string>>(new Map());

  // Load admin data after component mounts
  onMount(async () => {
    if (event.owned) {
      await loadAdminData();
    }
  });

  async function loadAdminData() {
    loading = true;
    try {
      const [attendeesResult, leaderboardResult, votesResult, referralsResult] = await Promise.all([
        EventsService.getEventAttendeesEventsAdminEventIdAttendeesGet({
          path: { event_id: event.id },
          throwOnError: false
        }),
        EventsService.getEventLeaderboardEventsAdminEventIdLeaderboardGet({
          path: { event_id: event.id },
          throwOnError: false
        }),
        EventsService.getEventVotesEventsAdminEventIdVotesGet({
          path: { event_id: event.id },
          throwOnError: false
        }),
        EventsService.getEventReferralsEventsAdminEventIdReferralsGet({
          path: { event_id: event.id },
          throwOnError: false
        })
      ]);

      if (attendeesResult.error) handleError(attendeesResult.error);
      else attendees = attendeesResult.data || [];

      if (leaderboardResult.error) handleError(leaderboardResult.error);
      else adminLeaderboard = leaderboardResult.data || [];

      if (votesResult.error) handleError(votesResult.error);
      else votes = votesResult.data || [];

      if (referralsResult.error) handleError(referralsResult.error);
      else referrals = referralsResult.data || [];
      
      // Build lookup maps from existing data
      buildLookupMaps();
    } catch (err) {
      handleError(err);
    } finally {
      loading = false;
    }
  }

  function buildLookupMaps() {
    // Build user lookup from attendees (for votes and referrals)
    userLookup.clear();
    attendees.forEach(attendee => {
      userLookup.set(attendee.id, `${attendee.first_name} ${attendee.last_name || ''}`.trim());
    });
    
    // Build project lookup from admin leaderboard
    projectLookup.clear();
    adminLeaderboard.forEach(project => {
      projectLookup.set(project.id, project.name);
    });
  }


  function isEventOwner(userId: string): boolean {
    const currentUser = getAuthenticatedUser();
    return currentUser.user.id === userId;
  }

  async function removeAttendee(userId: string) {
    // Prevent event owner from removing themselves
    if (isEventOwner(userId)) {
      toast.error('You cannot remove yourself from your own event');
      return;
    }

    try {
      const { error } = await EventsService.removeAttendeeEventsAdminEventIdRemoveAttendeePost({
        path: { event_id: event.id },
        body: userId,
        throwOnError: false
      });
      
      if (error) {
        handleError(error);
      } else {
        toast.success('Attendee removed');
        await loadAdminData();
      }
    } catch (err) {
      handleError(err);
    }
  }
</script>

{#if event.owned}
  <div class="divider">Admin Panel</div>
  
  {#if loading}
    <div class="flex justify-center py-8">
      <LoadingSpinner loadingText={returnLoadingText()} />
    </div>
  {:else}
    <div class="space-y-6">
      <!-- Event Management -->
      <div class="card bg-base-200">
        <div class="card-body">
          <h2 class="card-title">Event Management</h2>
          <UpdateEvent preselectedEvent={event} events={[event]} />
        </div>
      </div>

      <!-- Join Code Display -->
      <div class="card bg-base-200">
        <div class="card-body">
          <h2 class="card-title">Event Join Code</h2>
          <div class="flex items-center gap-2">
            <span class="badge badge-accent font-mono text-lg">
              {event.join_code}
            </span>
            <button 
              class="btn btn-sm btn-outline"
              onclick={() => {
                navigator.clipboard.writeText(event.join_code || '');
                toast.success('Join code copied to clipboard');
              }}
            >
              Copy
            </button>
          </div>
          <p class="text-sm text-base-content/70 mt-2">
            Share this code with people who want to join your event.
          </p>
          
          <div class="divider my-2"></div>
          <div class="space-y-2">
            <p class="text-sm font-medium">Share join link with attendees:</p>
            <div class="flex items-center gap-2">
              <input 
                type="text" 
                readonly 
                value={`${window.location.origin}/events/attend?join_code=${event.join_code}`}
                class="input input-bordered input-sm flex-1 font-mono text-xs"
              />
              <button 
                class="btn btn-sm btn-outline"
                onclick={() => {
                  navigator.clipboard.writeText(`${window.location.origin}/events/attend?join_code=${event.join_code}`);
                  toast.success('Join link copied to clipboard');
                }}
              >
                Copy Link
              </button>
            </div>
            <p class="text-xs text-base-content/60">
              When someone clicks this link, they will be automatically added to the event. To edit it, contact us.
            </p>
          </div>
        </div>
      </div>

      <!-- Attendees Table -->
      <AttendeesTable {attendees} onRemoveAttendee={removeAttendee} {event} />

      <!-- Admin Leaderboard -->
      <AdminLeaderboard projects={adminLeaderboard} />

      <!-- Votes Table -->
      <VotesTable {votes} userLookup={userLookup} {projectLookup} />

      <!-- Referrals Table -->
      <ReferralsTable {referrals} {userLookup} />
    </div>
  {/if}
{/if}
