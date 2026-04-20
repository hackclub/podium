<script lang="ts">
  import { onMount } from "svelte";
  import { SuperadminService, client } from "$lib/client/sdk.gen";
  import type { EventPrivate } from "$lib/client/types.gen";
  import { toast } from "svelte-sonner";

  type UserSummary = { id: string; email: string; display_name: string; is_superadmin: boolean };

  const phases = ["draft", "submission", "voting", "closed"];
  const repoValidations = ["none", "github", "custom"];
  const demoValidations = ["none", "itch", "custom"];
  const phaseBadge: Record<string, string> = {
    draft: "badge-ghost", submission: "badge-success", voting: "badge-warning", closed: "badge-info",
  };

  type Page<T> = { items: T[]; total: number; page: number; size: number; pages: number };

  let eventsPage = $state<Page<EventPrivate>>({ items: [], total: 0, page: 1, size: 25, pages: 0 });
  let usersPage = $state<Page<UserSummary>>({ items: [], total: 0, page: 1, size: 25, pages: 0 });
  let loading = $state(true);

  // Create form
  let newName = $state("");
  let newDesc = $state("");
  let newPhase = $state("draft");
  let creating = $state(false);

  // Edit state
  let editing = $state<EventPrivate | null>(null);
  let editOwnerEmail = $state("");
  let editRepoValidation = $state("");
  let editDemoValidation = $state("");
  let editCustomValidator = $state("");
  let editRequireYswsPii = $state(false);
  let saving = $state(false);

  async function loadEvents(page = eventsPage.page) {
    const { data, error } = await client.get<Page<EventPrivate>, unknown>({
      url: "/superadmin/events",
      query: { page, size: 25 },
      throwOnError: false,
    });
    if (error) toast.error("Failed to load events");
    else if (data) eventsPage = data;
  }

  async function loadUsers(page = usersPage.page) {
    const { data, error } = await client.get<Page<UserSummary>, unknown>({
      url: "/superadmin/users",
      query: { page, size: 25 },
      throwOnError: false,
    });
    if (error) toast.error("Failed to load users");
    else if (data) usersPage = data;
  }

  async function load() {
    await Promise.all([loadEvents(1), loadUsers(1)]);
    loading = false;
  }

  async function createEvent() {
    if (!newName.trim()) return;
    creating = true;
    const { data, error } = await SuperadminService.createEventSuperadminEventsPost({
      body: { name: newName.trim(), description: newDesc.trim(), phase: newPhase },
      throwOnError: false,
    });
    creating = false;
    if (error) { toast.error("Failed to create event"); return; }
    toast.success(`Event "${data!.name}" created`);
    newName = ""; newDesc = ""; newPhase = "draft";
    await loadEvents(1);
  }

  function startEdit(event: EventPrivate) {
    editing = event;
    editOwnerEmail = usersPage.items.find((u) => u.id === event.owner_id)?.email ?? "";
    editRepoValidation = event.repo_validation;
    editDemoValidation = event.demo_validation;
    editCustomValidator = event.custom_validator ?? "";
    editRequireYswsPii = event.require_ysws_pii;
  }

  async function saveEdit() {
    if (!editing) return;
    saving = true;
    const body: Record<string, string | boolean | null> = {};
    const ownerChanged = editOwnerEmail && usersPage.items.find((u) => u.id === editing!.owner_id)?.email !== editOwnerEmail;
    if (ownerChanged) body.owner_email = editOwnerEmail;
    if (editRepoValidation !== editing.repo_validation) body.repo_validation = editRepoValidation;
    if (editDemoValidation !== editing.demo_validation) body.demo_validation = editDemoValidation;
    const newCustom = editCustomValidator.trim() || null;
    if (newCustom !== (editing.custom_validator ?? null)) body.custom_validator = newCustom;
    if (editRequireYswsPii !== editing.require_ysws_pii) body.require_ysws_pii = editRequireYswsPii;

    if (Object.keys(body).length > 0) {
      const { error } = await client.patch<EventPrivate, unknown>({
        url: `/superadmin/events/${editing.id}`,
        body,
        throwOnError: false,
      });
      if (error) { toast.error("Save failed"); saving = false; return; }
    }
    toast.success("Event updated");
    editing = null;
    saving = false;
    await loadEvents();
  }

  async function deleteEvent(event: EventPrivate) {
    if (!confirm(`Soft-delete "${event.name}"?`)) return;
    const { error } = await SuperadminService.softDeleteEventSuperadminEventsEventIdDelete({
      path: { event_id: event.id },
      throwOnError: false,
    });
    if (error) { toast.error("Failed to delete event"); return; }
    toast.success("Event deleted");
    await loadEvents();
  }

  onMount(load);
</script>

<div class="max-w-5xl mx-auto space-y-8">
  <h1 class="text-3xl font-bold">Superadmin</h1>

  <!-- Create Event -->
  <div class="card bg-base-100 shadow-lg">
    <div class="card-body">
      <h2 class="card-title">Create Event</h2>
      <div class="flex flex-wrap gap-3">
        <input class="input input-bordered flex-1 min-w-48" placeholder="Event name" bind:value={newName} />
        <input class="input input-bordered flex-1 min-w-48" placeholder="Description" bind:value={newDesc} />
        <select class="select select-bordered" bind:value={newPhase}>
          {#each phases as p}<option value={p}>{p}</option>{/each}
        </select>
        <button class="btn btn-primary" onclick={createEvent} disabled={creating || !newName.trim()}>
          {creating ? "Creating…" : "Create"}
        </button>
      </div>
    </div>
  </div>

  <!-- Events Table -->
  <div class="card bg-base-100 shadow-lg">
    <div class="card-body">
      <h2 class="card-title">All Events</h2>
      {#if loading}
        <span class="loading loading-spinner loading-md"></span>
      {:else if eventsPage.total === 0}
        <p class="text-base-content/70">No events.</p>
      {:else}
        <div class="overflow-x-auto">
          <table class="table table-zebra w-full">
            <thead>
              <tr><th>Name</th><th>Phase</th><th>Repo</th><th>Demo</th><th>Owner</th><th>Deleted</th><th></th></tr>
            </thead>
            <tbody>
              {#each eventsPage.items as event (event.id)}
                <tr class={event.deleted_at ? "opacity-50" : ""}>
                  <td>
                    {#if !event.deleted_at}
                      <a href="/events/{event.slug}" class="link link-primary font-medium">{event.name}</a>
                    {:else}
                      <span class="line-through">{event.name}</span>
                    {/if}
                  </td>
                  <td><span class="badge {phaseBadge[event.phase] ?? 'badge-ghost'}">{event.phase}</span></td>
                  <td class="font-mono text-sm">{event.repo_validation}</td>
                  <td class="font-mono text-sm">{event.demo_validation}</td>
                  <td class="text-sm">{usersPage.items.find((u) => u.id === event.owner_id)?.email ?? event.owner_id}</td>
                  <td>{event.deleted_at ? new Date(event.deleted_at).toLocaleDateString() : "—"}</td>
                  <td class="flex gap-2">
                    {#if !event.deleted_at}
                      <button class="btn btn-outline btn-xs" onclick={() => startEdit(event)}>Edit</button>
                      <button class="btn btn-error btn-xs" onclick={() => deleteEvent(event)}>Delete</button>
                    {/if}
                  </td>
                </tr>
                {#if editing?.id === event.id}
                  <tr>
                    <td colspan="7">
                      <div class="card bg-base-200 my-2">
                        <div class="card-body gap-3 py-4">
                          <h3 class="font-semibold">Edit: {editing.name}</h3>
                          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                            <label class="form-control">
                              <span class="label-text mb-1">Owner email</span>
                              <input class="input input-bordered input-sm" bind:value={editOwnerEmail} />
                            </label>
                            <label class="form-control">
                              <span class="label-text mb-1">Repo validation</span>
                              <select class="select select-bordered select-sm" bind:value={editRepoValidation}>
                                {#each repoValidations as v}<option value={v}>{v}</option>{/each}
                              </select>
                            </label>
                            <label class="form-control">
                              <span class="label-text mb-1">Demo validation</span>
                              <select class="select select-bordered select-sm" bind:value={editDemoValidation}>
                                {#each demoValidations as v}<option value={v}>{v}</option>{/each}
                              </select>
                            </label>
                            <label class="form-control">
                              <span class="label-text mb-1">Custom validator key</span>
                              <input class="input input-bordered input-sm font-mono" placeholder="(none)" bind:value={editCustomValidator} />
                            </label>
                            <label class="flex items-center gap-2 cursor-pointer">
                              <input type="checkbox" class="checkbox checkbox-sm" bind:checked={editRequireYswsPii} />
                              <span class="label-text">Require YSWS PII (address + DOB)</span>
                            </label>
                          </div>
                          <div class="flex gap-2">
                            <button class="btn btn-primary btn-sm" onclick={saveEdit} disabled={saving}>
                              {saving ? "Saving…" : "Save"}
                            </button>
                            <button class="btn btn-ghost btn-sm" onclick={() => editing = null}>Cancel</button>
                          </div>
                        </div>
                      </div>
                    </td>
                  </tr>
                {/if}
              {/each}
            </tbody>
          </table>
        </div>
        {#if eventsPage.pages > 1}
          <div class="flex items-center gap-2 mt-3">
            <button class="btn btn-sm btn-ghost" disabled={eventsPage.page === 1} onclick={() => loadEvents(eventsPage.page - 1)}>‹</button>
            <span class="text-sm">Page {eventsPage.page} of {eventsPage.pages}</span>
            <button class="btn btn-sm btn-ghost" disabled={eventsPage.page === eventsPage.pages} onclick={() => loadEvents(eventsPage.page + 1)}>›</button>
          </div>
        {/if}
      {/if}
    </div>
  </div>

  <!-- Users Table -->
  <div class="card bg-base-100 shadow-lg">
    <div class="card-body">
      <h2 class="card-title">Users</h2>
      {#if loading}
        <span class="loading loading-spinner loading-md"></span>
      {:else if usersPage.total === 0}
        <p class="text-base-content/70">No users.</p>
      {:else}
        <div class="overflow-x-auto">
          <table class="table table-zebra w-full">
            <thead>
              <tr><th>Email</th><th>Display name</th><th>Superadmin</th><th>ID</th></tr>
            </thead>
            <tbody>
              {#each usersPage.items as u (u.id)}
                <tr>
                  <td>{u.email}</td>
                  <td>{u.display_name || "—"}</td>
                  <td>{u.is_superadmin ? "✓" : ""}</td>
                  <td class="font-mono text-xs text-base-content/50">{u.id}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
        {#if usersPage.pages > 1}
          <div class="flex items-center gap-2 mt-3">
            <button class="btn btn-sm btn-ghost" disabled={usersPage.page === 1} onclick={() => loadUsers(usersPage.page - 1)}>‹</button>
            <span class="text-sm">Page {usersPage.page} of {usersPage.pages}</span>
            <button class="btn btn-sm btn-ghost" disabled={usersPage.page === usersPage.pages} onclick={() => loadUsers(usersPage.page + 1)}>›</button>
          </div>
        {/if}
      {/if}
    </div>
  </div>
</div>
