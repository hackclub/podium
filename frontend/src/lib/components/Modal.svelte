<script lang="ts">
  /* How to use:
    import Modal from "$lib/components/Modal.svelte";
    let variableToHoldModal: Modal = $state() as Modal;  
    <Modal bind:this={variableToHoldModal} title="abxyz">
        <p class="py-4">
            Look! A paragraph!
        </p>
        <ul>
            <li>Look! It's a list!</li>
        </ul>
    </Modal>
    */

  import type { Snippet } from "svelte";

  let { title, children }: { title: string; children: Snippet } = $props();

  let modalDialog: HTMLDialogElement | null = $state(null);
  export function closeModal() {
    if (modalDialog) {
      modalDialog.close();
    }
  }
  export function openModal() {
    if (modalDialog) {
      modalDialog.showModal();
    }
  }
  export function toggleModal() {
    if (modalDialog) {
      if (modalDialog.open) {
        modalDialog.close();
      } else {
        modalDialog.showModal();
      }
    }
  }
</script>

<dialog class="modal modal-bottom sm:modal-middle" bind:this={modalDialog}>
  <div class="modal-box">
    <h2 class="font-bold text-lg">{title}</h2>
    {@render children?.()}
    <div class="modal-action">
      <button class="btn" onclick={closeModal}>Close</button>
    </div>
  </div>
  <form method="dialog" class="modal-backdrop">
    <button>close</button>
  </form>
</dialog>
