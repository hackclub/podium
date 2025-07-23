<script lang="ts">
  import { PUBLIC_API_URL } from "$env/static/public";
  let data = $state([]);
  const reload = async () => {
    const res = await fetch(`${PUBLIC_API_URL}letter_box`, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    });
    if (res.ok) {
      const json = await res.json();
      data = json;
      console.log(data);
    } else {
      //        handleError(res);
    }
  };
  reload();
</script>

<div class="hero">
  <div class=" hero-content text-left">
    <div class="max-w-md">
      <h1 class="text-4xl font-bold">Letter box</h1>
      <button class="btn btn-primary" onclick={() => reload()}>Reload</button>
      <br />
      {#if data && data.length === 0}
        <p class="text-base-content/70">No letters found.</p>
      {:else}
        <ul class="list-disc pl-5">
          {#each data as letter}
            <li class="mb-2">
              <strong>{letter[0]}:</strong>
              {#let url = new URL(letter[1])}
              <a href={url.pathname + url.search}>{letter[1]}</a>
            </li>
          {/each}
        </ul>
      {/if}
    </div>
  </div>
</div>
