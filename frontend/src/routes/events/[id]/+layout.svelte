<script lang="ts">
  let { children, data } = $props();
</script>

<div class="text-center p-4">
  <h1 class="text-2xl font-semibold">{data.event.name}</h1>
  <p class="text-accent">{data.event.description}</p>
</div>

{@render children()}
