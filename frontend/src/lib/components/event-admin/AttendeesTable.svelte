<script lang="ts">
  import type { UserAttendee, Event } from '$lib/client/types.gen';
  import ConfirmationModal from '$lib/components/ConfirmationModal.svelte';
  import { getAuthenticatedUser } from '$lib/user.svelte';

  interface Props {
    attendees: UserAttendee[];
    onRemoveAttendee: (userId: string) => Promise<void>;
    event: Event & { owned: boolean; partOfEvent: boolean; join_code?: string };
  }

  let { attendees, onRemoveAttendee, event }: Props = $props();
  let removeConfirmation: ConfirmationModal = $state() as ConfirmationModal;
  let attendeeToRemove: string = $state('');

  function isEventOwner(userId: string): boolean {
    const currentUser = getAuthenticatedUser();
    return currentUser.user.id === userId;
  }

  function confirmRemoveAttendee(userId: string) {
    attendeeToRemove = userId;
    removeConfirmation.open();
  }

  async function handleRemoveAttendee() {
    await onRemoveAttendee(attendeeToRemove);
  }
</script>

<div class="card bg-base-200">
  <div class="card-body">
    <h2 class="card-title">Event Attendees ({attendees.length})</h2>
    
    {#if event.owned && !event.partOfEvent}
      <div class="alert alert-info mb-4">
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" class="stroke-current shrink-0 w-6 h-6"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
        <div>
          <h3 class="font-bold">You're not attending this event as a participant</h3>
          <div class="text-xs">You can <a href="/events/attend?join_code={event.join_code}&referral=Event%20Owner" class="link link-primary">join the event</a> if you wish to also be able to act as an attendee.</div>
        </div>
      </div>
    {/if}
    
    {#if attendees.length === 0}
      <p class="text-base-content/70">No attendees yet.</p>
    {:else}
      <div class="overflow-x-auto">
        <table class="table table-zebra w-full">
          <thead>
            <tr>
              <th>Name</th>
              <th>Display Name</th>
              <th>Email</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {#each attendees as attendee}
              <tr>
                <td class="font-medium">
                  {attendee.first_name} {attendee.last_name || ''}
                </td>
                <td>{attendee.display_name || '-'}</td>
                <td>{attendee.email}</td>
                <td>
                  <button 
                    class="btn btn-sm btn-error {isEventOwner(attendee.id) ? 'btn-disabled' : ''}"
                    onclick={() => confirmRemoveAttendee(attendee.id)}
                    disabled={isEventOwner(attendee.id)}
                    title={isEventOwner(attendee.id) ? 'You cannot remove yourself from your own event' : ''}
                  >
                    Remove
                  </button>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/if}
  </div>
</div>

<ConfirmationModal
  bind:this={removeConfirmation}
  title="Remove Attendee"
  message="Are you sure you want to remove this attendee from the event?"
  confirmText="Remove"
  cancelText="Cancel"
  confirmClass="btn-error"
  onConfirm={handleRemoveAttendee}
  onCancel={() => {}}
/>
