<script lang="ts">
  import { UsersService } from "$lib/client/sdk.gen";
  import type { UserPrivate } from "$lib/client";
  import { toast } from "svelte-sonner";
  import { handleError, invalidateUser } from "$lib/misc";
  import { fade } from "svelte/transition";
  import Modal from "$lib/components/Modal.svelte";

  let { user }: { user: UserPrivate } = $props();
  
  let updateModal: Modal = $state() as Modal;

  async function updateUser() {
    // If display_name is empty or whitespace, set it to 'FirstName LastInitial.'
    if (!user.display_name || user.display_name.trim() === "") {
      const first = user.first_name?.trim() || "";
      const lastInitial = user.last_name?.trim() ? user.last_name.trim()[0] + "." : "";
      user.display_name = `${first} ${lastInitial}`.trim();
    }
    try {
      await UsersService.updateCurrentUserUsersCurrentPut({
        body: user,
        throwOnError: true,
      });
      toast.success("Profile updated successfully");
      await invalidateUser();
      updateModal.closeModal();
    } catch (err) {
      handleError(err);
    }
  }
</script>

<button class="btn btn-outline btn-sm" onclick={() => {updateModal.openModal()}}>
  Edit Profile
</button>

<Modal
  bind:this={updateModal}
  title="Update Profile"
>
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

        <label class="label" for="street_1">Address Line 1</label>
        <input
          id="street_1"
          type="text"
          bind:value={user.street_1}
          placeholder="123 Main St"
          class="input input-bordered w-full"
        />

        <label class="label" for="street_2">Address Line 2</label>
        <input
          id="street_2"
          type="text"
          bind:value={user.street_2}
          placeholder="Apt 4B"
          class="input input-bordered w-full"
        />

        <label class="label" for="city">City</label>
        <input
          id="city"
          type="text"
          bind:value={user.city}
          placeholder="New York"
          class="input input-bordered w-full"
        />

        <label class="label" for="state">State</label>
        <input
          id="state"
          type="text"
          bind:value={user.state}
          placeholder="NY"
          class="input input-bordered w-full"
        />

        <label class="label" for="zip_code">ZIP Code</label>
        <input
          id="zip_code"
          type="text"
          bind:value={user.zip_code}
          placeholder="10001"
          class="input input-bordered w-full"
        />

        <label class="label" for="country">Country</label>
        <input
          id="country"
          type="text"
          bind:value={user.country}
          placeholder="United States"
          class="input input-bordered w-full"
        />

        <label class="label" for="dob">Date of Birth</label>
        <input
          id="dob"
          type="date"
          bind:value={user.dob}
          class="input input-bordered w-full"
        />

        <button class="btn btn-block mt-4 btn-primary" onclick={updateUser}>
          Update Profile
        </button>
      </fieldset>
    </div>
  </div>
</Modal> 