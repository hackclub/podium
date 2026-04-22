<script lang="ts">
  import type { UserUpdate } from "$lib/client";

  let { data = $bindable(), markRequired = false }: { data: UserUpdate; markRequired?: boolean } = $props();
</script>

<label class="label" for="af_street_1">Address Line 1 {#if markRequired}<span class="text-error">*</span>{/if}</label>
<input id="af_street_1" type="text" bind:value={data.street_1} placeholder="123 Main St" class="input input-bordered w-full" required={markRequired} />

<label class="label" for="af_street_2">Address Line 2</label>
<input id="af_street_2" type="text" bind:value={data.street_2} placeholder="Apt 4B" class="input input-bordered w-full" />

<label class="label" for="af_city">City {#if markRequired}<span class="text-error">*</span>{/if}</label>
<input id="af_city" type="text" bind:value={data.city} placeholder="New York" class="input input-bordered w-full" required={markRequired} />

<label class="label" for="af_state">State / Province</label>
<input id="af_state" type="text" bind:value={data.state} placeholder="NY" class="input input-bordered w-full" />

<label class="label" for="af_zip">ZIP / Postal Code</label>
<input id="af_zip" type="text" bind:value={data.zip_code} placeholder="10001" class="input input-bordered w-full" />

<label class="label" for="af_country">Country {#if markRequired}<span class="text-error">*</span>{/if}</label>
<input id="af_country" type="text" bind:value={data.country} placeholder="United States" class="input input-bordered w-full" required={markRequired} />

<label class="label" for="af_dob">Date of Birth {#if markRequired}<span class="text-error">*</span>{/if}</label>
<input id="af_dob" type="date" bind:value={data.dob} class="input input-bordered w-full" required={markRequired} />
