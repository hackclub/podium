<script lang="ts">
  import { fade } from "svelte/transition";
  import Modal from "./Modal.svelte";

  interface Props {
    title: string;
    message: string;
    confirmText?: string;
    cancelText?: string;
    confirmClass?: string;
    onConfirm: () => void;
    onCancel: () => void;
  }

  let {
    title,
    message,
    confirmText = "Confirm",
    cancelText = "Cancel",
    confirmClass = "btn-error",
    onConfirm,
    onCancel,
  }: Props = $props();

  let modal: Modal = $state() as Modal;

  function open() {
    modal.openModal();
  }

  function close() {
    modal.closeModal();
  }

  function handleConfirm() {
    onConfirm();
    close();
  }

  function handleCancel() {
    onCancel();
    close();
  }

  // Expose methods for parent components
  export { open, close };
</script>

<Modal bind:this={modal} {title}>
  <div class="p-4">
    <div role="alert" class="alert" in:fade out:fade>
      <span>{message}</span>
      <div class="flex gap-2">
        <button class="btn" onclick={handleCancel}>
          {cancelText}
        </button>
        <button class="btn {confirmClass}" onclick={handleConfirm}>
          {confirmText}
        </button>
      </div>
    </div>
  </div>
</Modal>
