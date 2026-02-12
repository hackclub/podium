<script>
  import { goto } from "$app/navigation";
  import { toast } from "svelte-sonner";
</script>

<button
  onclick={() => {
    toast("enjoy the loading animation :)");
    goto("/load/forever");
  }}
  class="btn btn-block flex flex-col justify-center min-h-screen"
  >Stare at the loading animation</button
>
