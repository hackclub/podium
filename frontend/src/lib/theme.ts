import CampfireFlagship from './logos/CampfireFlagship.svelte';
import CampfireSatLogo from './logos/CampfireSat.svelte';
import SleepoverLogo from './logos/Sleepover.svelte';
import SunbeamLogo from './logos/Sunbeam.svelte';
import HavenLogo from './logos/Haven.svelte';
import type { ApiEvent } from './api';

export type EventTheme = {
	logo: import('svelte').Component<any>;
	background: string;
	font: string;
	primary: string;
	selected: string;
	skin: EventSkin;
};

/**
 * Colors and fonts for the cards, text and controls drawn over an event's
 * background. The event layout exposes each one as a CSS variable (`skin.ink`
 * is `--ink`, `skin.headingFont` is `--heading-font`, ...) so pages can use
 * them in class names, opacity modifiers included: `text-(--ink)/70`.
 */
export type EventSkin = {
	/** Card fill */
	surface: string;
	/** Fill of cards inside a card: project tiles, leaderboard rows */
	tile: string;
	/** Text on cards */
	ink: string;
	/** Card border */
	edge: string;
	/** Borders of fields, tiles and dividers */
	line: string;
	/** Text in the accent color: focused labels, selected tiles, links */
	accentInk: string;
	/** Text on an accent fill: badges, the teammate Add button */
	onAccent: string;
	button: string;
	buttonInk: string;
	buttonHoverInk: string;
	/** Input fill */
	field: string;
	headingFont: string;
	/** Drop shadow behind text on cards */
	shade: string;
	danger: string;
	success: string;
	/** Leaderboard rank colors for 1st, 2nd and 3rd */
	gold: string;
	silver: string;
	bronze: string;
};

/** The classic look: a card in the primary color with white text and borders. */
function defaultSkin(font: string, primary: string, selected: string): EventSkin {
	return {
		surface: primary,
		tile: primary,
		ink: '#fff',
		edge: '#fff',
		line: '#fff',
		accentInk: selected,
		onAccent: '#fff',
		button: '#fff',
		buttonInk: primary,
		buttonHoverInk: '#fff',
		field: 'transparent',
		headingFont: font,
		shade: '0 3px 3px rgb(0 0 0 / 0.12)',
		danger: '#fca5a5',
		success: '#86efac',
		gold: '#facc15',
		silver: '#d1d5db',
		bronze: '#d97706'
	};
}

const skins: Record<string, (font: string, primary: string, selected: string) => Partial<EventSkin>> = {
	// Matches haven.hackclub.com: white panels with orange text, cream fields
	// and orange pill buttons.
	haven: (font, primary) => ({
		surface: '#fff',
		tile: '#fff6e3',
		ink: primary,
		line: '#f7c9a1',
		accentInk: primary,
		onAccent: primary,
		button: primary,
		buttonInk: '#fff',
		buttonHoverInk: primary,
		field: 'rgb(255 246 227 / 0.9)',
		headingFont: `"Darumadrop One", ${font}`,
		shade: '0 0 #0000',
		danger: '#c62828',
		success: '#4d7c0f',
		gold: '#fba71f',
		silver: '#a8a29e',
		bronze: '#b8774a'
	})
};

/** The skin as CSS custom properties, for a `style` attribute. */
export function skinStyle(skin: EventSkin): string {
	return Object.entries(skin)
		.map(([key, value]) => `--${key.replace(/[A-Z]/g, (c) => '-' + c.toLowerCase())}: ${value};`)
		.join(' ');
}

// Default themes used as fallbacks
export const defaultThemes: Record<string, Omit<EventTheme, 'logo' | 'skin'>> = {
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
	},
	sleepover: {
		background: 'https://cdn.hackclub.com/019c4e31-db5f-7af0-848d-fc4cc15a9c33/image.png',
		font: '"Ember& Fire", sans-serif',
		primary: '#49B6F3',
		selected: '#F59E0B'
	},
	sunbeam: {
		background: '/sunbeam-background.webp',
		font: '"Galindo", sans-serif',
		primary: '#0e387a',
		selected: '#F59E0B'
	},
	haven: {
		background: '/haven-background.webp',
		font: '"Jua Extras", "Jua", sans-serif',
		primary: '#ed5615',
		selected: '#ffd059'
	}
};

export function getLogo(themeName: string): import('svelte').Component<any> {
	if (themeName === 'campfire') return CampfireSatLogo;
	if (themeName === 'flagship') return CampfireFlagship;
	if (themeName === 'sleepover') return SleepoverLogo;
	if (themeName === 'sunbeam') return SunbeamLogo;
	return HavenLogo;
}

/** The theme for a preset, with an event's own overrides applied. Unknown presets fall back to Haven. */
export function buildTheme(
	themeName: string,
	overrides: Partial<Pick<ApiEvent, 'theme_background' | 'theme_font' | 'theme_primary' | 'theme_selected'>> = {}
): EventTheme {
	const preset = themeName in defaultThemes ? themeName : 'haven';
	const defaults = defaultThemes[preset];
	const font = overrides.theme_font || defaults.font;
	const primary = overrides.theme_primary || defaults.primary;
	const selected = overrides.theme_selected || defaults.selected;
	return {
		logo: getLogo(preset),
		background: overrides.theme_background || defaults.background,
		font,
		primary,
		selected,
		skin: {
			...defaultSkin(font, primary, selected),
			...skins[preset]?.(font, primary, selected)
		}
	};
}

export function eventToTheme(event: ApiEvent): EventTheme {
	return buildTheme(event.theme_name, event);
}
