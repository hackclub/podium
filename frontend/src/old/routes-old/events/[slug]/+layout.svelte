<script lang="ts">
  let { children, data } = $props();
</script>

<div class="text-center p-4">
  <h1 class="text-2xl font-semibold">
    <a href="/events/{data.event.slug}" class="link hover-link">
      {data.event.name}
    </a>
  </h1>
  <p class="text-accent">{data.event.description}</p>
</div>

{@render children()}
