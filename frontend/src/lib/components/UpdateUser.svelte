<script lang="ts">
  import { UsersService } from "$lib/client/sdk.gen";
  import type { UserUpdate } from "$lib/client";
  import AddressFields from "./AddressFields.svelte";
  import { toast } from "svelte-sonner";
  import { handleError, invalidateUser } from "$lib/misc";
  import { asyncClick } from "$lib/actions/asyncClick";
  import { fade } from "svelte/transition";
  import Modal from "$lib/components/Modal.svelte";

  let { user }: { user: UserUpdate } = $props();

  let updateModal: Modal = $state() as Modal;

  async function updateUser() {
    // If display_name is empty or whitespace, set it to 'FirstName LastInitial.'
    if (!user.display_name || user.display_name.trim() === "") {
      const first = user.first_name?.trim() || "";
      const lastInitial = user.last_name?.trim()
        ? user.last_name.trim()[0] + "."
        : "";
      user.display_name = `${first} ${lastInitial}`.trim();
    }
    const { data, error: err } =
      await UsersService.updateCurrentUserUsersCurrentPut({
        body: user,
        throwOnError: false,
      });
    if (err || !data) {
      handleError(err);
      return;
    }
    toast.success("Profile updated successfully");
    await invalidateUser();
    updateModal.closeModal();
  }
</script>

<button
  class="btn btn-outline btn-sm"
  onclick={() => {
    updateModal.openModal();
  }}
>
  Edit Profile
</button>

<Modal bind:this={updateModal} title="Update Profile">
  <div class="p-4 max-w-md mx-auto">
    <div class="space-y-4">
      <fieldset class="fieldset">
        <label class="label" for="first_name">First Name</label>
        <input
          id="first_name"
          type="text"
          bind:value={user.first_name}
          placeholder="First Name"
          class="input input-bordered w-full"
        />

        <label class="label" for="last_name">Last Name</label>
        <input
          id="last_name"
          type="text"
          bind:value={user.last_name}
          placeholder="Last Name"
          class="input input-bordered w-full"
        />

        <label class="label" for="display_name">Display Name</label>
        <input
          id="display_name"
          type="text"
          bind:value={user.display_name}
          placeholder="Display Name"
          class="input input-bordered w-full"
        />

        <label class="label" for="phone">Phone</label>
        <input
          id="phone"
          type="tel"
          bind:value={user.phone}
          placeholder="+15555555555"
          class="input input-bordered w-full"
        />

        <AddressFields bind:data={user} />

        <button class="btn btn-block mt-4 btn-primary" use:asyncClick={updateUser}>
          Update Profile
        </button>
      </fieldset>
    </div>
  </div>
</Modal>
