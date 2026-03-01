<script lang="ts">
	import { onMount } from 'svelte';
	import {
		getPublicDashboard,
		type PublicDashboard
	} from '$lib/api';
	import {
		Chart,
		BarController,
		BarElement,
		CategoryScale,
		LinearScale,
		Tooltip,
		Legend
	} from 'chart.js';
	import '../../app.css';

	Chart.register(BarController, BarElement, CategoryScale, LinearScale, Tooltip, Legend);

	let data: PublicDashboard | null = $state(null);
	let loading = $state(true);
	let error = $state('');

	let shipRateCanvas: HTMLCanvasElement | undefined = $state();
	let projectsCanvas: HTMLCanvasElement | undefined = $state();

	let shipRateChart: Chart | null = null;
	let projectsChart: Chart | null = null;

	let sortBy = $state<'attendees' | 'shippers' | 'projects' | 'ship_rate' | 'checkins' | 'scanned_day1' | 'scanned_day2' | 'scanned_either'>('ship_rate');
	let sortDir = $state<'asc' | 'desc'>('desc');
	let search = $state('');

	function toggleSort(col: typeof sortBy) {
		if (sortBy === col) {
			sortDir = sortDir === 'desc' ? 'asc' : 'desc';
		} else {
			sortBy = col;
			sortDir = 'desc';
		}
	}

	const sortKeyMap: Record<typeof sortBy, keyof (typeof data extends null ? never : NonNullable<typeof data>['events'][0])> = {
		attendees: 'attendee_count',
		shippers: 'shipper_count',
		projects: 'project_count',
		ship_rate: 'ship_rate',
		checkins: 'checkin_count',
		scanned_day1: 'scanned_day1_count',
		scanned_day2: 'scanned_day2_count',
		scanned_either: 'scanned_either_day_count',
	};

	const filteredAndSortedEvents = $derived(() => {
		if (!data) return [];
		const q = search.toLowerCase();
		const filtered = q
			? data.events.filter((e) => e.name.toLowerCase().includes(q) || e.slug.toLowerCase().includes(q))
			: [...data.events];
		const key = sortKeyMap[sortBy];
		const dir = sortDir === 'desc' ? -1 : 1;
		return filtered.sort((a, b) => (a[key] - b[key]) * dir);
	});

	async function fetchData() {
		try {
			data = await getPublicDashboard();
			error = '';
		} catch (e: any) {
			error = e.message || 'Failed to load dashboard';
		} finally {
			loading = false;
		}
	}

	onMount(() => {
		fetchData();
		const interval = setInterval(fetchData, 60_000);
		return () => clearInterval(interval);
	});

	$effect(() => {
		if (!data || !shipRateCanvas || !projectsCanvas) return;

		const byShipRate = [...data.events]
			.filter((e) => e.scanned_either_day_count > 0)
			.sort((a, b) => b.ship_rate - a.ship_rate)
			.slice(0, 20);

		const byProjects = [...data.events]
			.filter((e) => e.project_count > 0)
			.sort((a, b) => b.project_count - a.project_count)
			.slice(0, 20);

		const chartFont = { family: 'ui-monospace, monospace', size: 11 };
		const gridColor = 'rgba(255,255,255,0.06)';
		const tickColor = 'rgba(255,255,255,0.4)';

		shipRateChart?.destroy();
		shipRateChart = new Chart(shipRateCanvas, {
			type: 'bar',
			data: {
				labels: byShipRate.map((e) => truncate(e.name, 20)),
				datasets: [
					{
						label: 'Shipped (%)',
						data: byShipRate.map((e) => e.ship_rate),
						backgroundColor: 'rgba(74, 222, 128, 0.6)',
						borderColor: 'rgba(74, 222, 128, 1)',
						borderWidth: 1,
						borderRadius: 3
					},
					{
						label: 'Scanned (Any)',
						data: byShipRate.map((e) => e.scanned_either_day_count),
						backgroundColor: 'rgba(96, 165, 250, 0.4)',
						borderColor: 'rgba(96, 165, 250, 1)',
						borderWidth: 1,
						borderRadius: 3
					}
				]
			},
			options: {
				responsive: true,
				maintainAspectRatio: false,
				plugins: {
					legend: { labels: { color: tickColor, font: chartFont } },
					tooltip: {
						callbacks: {
							afterBody: (items) => {
								const idx = items[0]?.dataIndex;
								if (idx === undefined) return '';
								const ev = byShipRate[idx];
								return `Projects: ${ev.project_count} / ${ev.scanned_either_day_count} scanned`;
							}
						}
					}
				},
				scales: {
					x: { ticks: { color: tickColor, font: chartFont, maxRotation: 45 }, grid: { color: gridColor } },
					y: { ticks: { color: tickColor, font: chartFont }, grid: { color: gridColor } }
				}
			}
		});

		projectsChart?.destroy();
		projectsChart = new Chart(projectsCanvas, {
			type: 'bar',
			data: {
				labels: byProjects.map((e) => truncate(e.name, 20)),
				datasets: [
					{
						label: 'Projects Shipped',
						data: byProjects.map((e) => e.project_count),
						backgroundColor: 'rgba(168, 85, 247, 0.6)',
						borderColor: 'rgba(168, 85, 247, 1)',
						borderWidth: 1,
						borderRadius: 3
					}
				]
			},
			options: {
				responsive: true,
				maintainAspectRatio: false,
				plugins: {
					legend: { labels: { color: tickColor, font: chartFont } }
				},
				scales: {
					x: { ticks: { color: tickColor, font: chartFont, maxRotation: 45 }, grid: { color: gridColor } },
					y: { ticks: { color: tickColor, font: chartFont }, grid: { color: gridColor } }
				}
			}
		});

		return () => {
			shipRateChart?.destroy();
			projectsChart?.destroy();
		};
	});

	function truncate(s: string, max: number) {
		return s.length > max ? s.slice(0, max - 1) + '\u2026' : s;
	}
</script>

<svelte:head>
	<title>Campfire Dashboard - Podium</title>
</svelte:head>

<div class="min-h-screen bg-[#111] p-8">
	<div class="max-w-7xl mx-auto">
		<div class="mb-8">
			<div class="flex items-center gap-3 mb-1">
				<img src="/favicon.svg" alt="Podium" class="h-7" />
				<h1 class="text-3xl font-bold text-white">Campfire Dashboard</h1>
			</div>
			<p class="text-white/40 text-sm mt-1">
				Overview of shipping across all campfire events
			</p>
		</div>

		{#if loading}
			<p class="text-white/60">Loading dashboard...</p>
		{:else if error}
			<p class="text-red-400">{error}</p>
		{:else if data}
			<!-- Summary cards -->
			<div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4 mb-8">
				<div class="rounded-lg border border-white/10 bg-white/5 p-4">
					<p class="text-white/40 text-xs uppercase tracking-wider">Unique Shippers</p>
					<p class="text-3xl font-bold text-white mt-1">{data.total_shippers.toLocaleString()}</p>
				</div>
				<div class="rounded-lg border border-white/10 bg-white/5 p-4">
					<p class="text-white/40 text-xs uppercase tracking-wider">Total Projects</p>
					<p class="text-3xl font-bold text-white mt-1">{data.total_projects.toLocaleString()}</p>
				</div>
				<div class="rounded-lg border border-white/10 bg-white/5 p-4">
					<p class="text-white/40 text-xs uppercase tracking-wider">Total Attendees</p>
					<p class="text-3xl font-bold text-white mt-1">{data.total_attendees.toLocaleString()}</p>
				</div>
				<div class="rounded-lg border border-white/10 bg-white/5 p-4">
					<p class="text-white/40 text-xs uppercase tracking-wider">Checked In</p>
					<p class="text-3xl font-bold text-white mt-1">{data.total_checkins.toLocaleString()}</p>
				</div>
				<div class="rounded-lg border border-white/10 bg-white/5 p-4">
					<p class="text-white/40 text-xs uppercase tracking-wider">Scanned (Any Day)</p>
					<p class="text-3xl font-bold text-white mt-1">{data.total_scanned_either_day.toLocaleString()}</p>
				</div>
			</div>

			<!-- Event table -->
			<div class="rounded-lg border border-white/10 bg-white/5 p-4 mb-8">
				<div class="flex items-center justify-between mb-4">
					<h2 class="text-sm font-medium text-white/60">All Campfire Events</h2>
					<input
						type="text"
						placeholder="Search events..."
						class="bg-white/5 border border-white/10 rounded-md px-3 py-1.5 text-xs text-white placeholder-white/30 outline-none focus:border-white/20 w-48"
						bind:value={search}
					/>
				</div>
				<div class="overflow-x-auto">
					<table class="w-full text-sm">
						<thead>
							<tr class="text-left text-white/40 border-b border-white/10">
								<th class="pb-3 pr-4">Event</th>
								{#each [
									{ key: 'attendees', label: 'Attendees' },
									{ key: 'checkins', label: 'Checked In' },
									{ key: 'scanned_day1', label: 'Scanned D1' },
									{ key: 'scanned_day2', label: 'Scanned D2' },
									{ key: 'scanned_either', label: 'Scanned (Any)' },
									{ key: 'shippers', label: 'Shippers' },
									{ key: 'projects', label: 'Projects' },
									{ key: 'ship_rate', label: 'Ship Rate' }
								] as col}
									<th class="pb-3 pr-4 text-right">
										<button
											type="button"
											class="inline-flex items-center gap-1 hover:text-white transition-colors {sortBy === col.key ? 'text-white' : ''}"
											onclick={() => toggleSort(col.key as typeof sortBy)}
										>
											{col.label}
											{#if sortBy === col.key}
												<span class="text-[10px]">{sortDir === 'desc' ? '▼' : '▲'}</span>
											{/if}
										</button>
									</th>
								{/each}
							</tr>
						</thead>
						<tbody>
							{#each filteredAndSortedEvents() as event}
								<tr class="border-b border-white/5 hover:bg-white/5">
									<td class="py-3 pr-4">
										<span class="text-white font-medium">{event.name}</span>
										<span class="text-white/30 text-xs ml-2">/{event.slug}</span>
									</td>
									<td class="py-3 pr-4 text-right text-white/60">{event.attendee_count}</td>
									<td class="py-3 pr-4 text-right text-white/60">{event.checkin_count}</td>
									<td class="py-3 pr-4 text-right text-white/60">{event.scanned_day1_count}</td>
									<td class="py-3 pr-4 text-right text-white/60">{event.scanned_day2_count}</td>
									<td class="py-3 pr-4 text-right text-white/60">{event.scanned_either_day_count}</td>
									<td class="py-3 pr-4 text-right text-white/60">{event.shipper_count}</td>
									<td class="py-3 pr-4 text-right text-white/60">{event.project_count}</td>
									<td class="py-3 pr-4 text-right">
										<span
											class="px-2 py-0.5 rounded text-xs {event.ship_rate >= 50
												? 'bg-green-500/20 text-green-400'
												: event.ship_rate >= 25
													? 'bg-yellow-500/20 text-yellow-400'
													: 'bg-red-500/20 text-red-400'}"
										>
											{event.ship_rate}%
										</span>
									</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
				<p class="text-white/30 text-xs mt-3">{filteredAndSortedEvents().length} of {data.events.length} campfire events</p>
			</div>

			<!-- Charts -->
			<div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
				<div class="rounded-lg border border-white/10 bg-white/5 p-4">
					<h2 class="text-sm font-medium text-white/60 mb-3">Ship Rate by Event (% of scanned who shipped)</h2>
					<div class="h-72">
						<canvas bind:this={shipRateCanvas}></canvas>
					</div>
				</div>
			</div>

			<div class="rounded-lg border border-white/10 bg-white/5 p-4 mb-8">
				<h2 class="text-sm font-medium text-white/60 mb-3">Projects Shipped by Event</h2>
				<div class="h-72">
					<canvas bind:this={projectsCanvas}></canvas>
				</div>
			</div>
		{/if}
	</div>
</div>
