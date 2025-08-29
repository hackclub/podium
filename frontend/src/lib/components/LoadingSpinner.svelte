<script lang="ts">
  export let loadingText: string;
</script>

<div class="flex items-center justify-center min-h-screen flex-col">
  <span class="loading loading-ball loading-lg mb-2"></span>
  <p>{loadingText}</p>
</div>
