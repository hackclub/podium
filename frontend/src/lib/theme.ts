import CampfireFlagship from './logos/CampfireFlagship.svelte';
import CampfireSatLogo from './logos/CampfireSat.svelte';
import type { ApiEvent } from './api';

export type EventTheme = {
	logo: import('svelte').Component<any>;
	background: string;
	font: string;
	primary: string;
	selected: string;
};

// Default themes used as fallbacks
export const defaultThemes: Record<string, Omit<EventTheme, 'logo'>> = {
	campfire: {
		background: 'https://cdn.hackclub.com/019c4e31-db5f-7af0-848d-fc4cc15a9c33/image.png',
		font: '"Ember& Fire", sans-serif',
		primary: '#49B6F3',
		selected: '#F59E0B'
	},
	flagship: {
		background: 'https://cdn.hackclub.com/019c4e9a-2d12-728d-b2b1-a238ca90b7db/image.png',
		font: '"ADLaM Display", sans-serif',
		primary: '#000',
		selected: '#F59E0B'
	}
};

export function getLogo(themeName: string): import('svelte').Component<any> {
	return themeName === 'flagship' ? CampfireFlagship : CampfireSatLogo;
}

export function eventToTheme(event: ApiEvent): EventTheme {
	const defaults = defaultThemes[event.theme_name] || defaultThemes.campfire;
	return {
		logo: getLogo(event.theme_name),
		background: event.theme_background || defaults.background,
		font: event.theme_font || defaults.font,
		primary: event.theme_primary || defaults.primary,
		selected: event.theme_selected || defaults.selected
	};
}
