import CampfireFlagship from './logos/CampfireFlagship.svelte';
import CampfireSatLogo from './logos/CampfireSat.svelte';

export const theme: Record<string, EventTheme> = {
	campfire: {
		logo: CampfireSatLogo,
		background: 'https://cdn.hackclub.com/019c4e31-db5f-7af0-848d-fc4cc15a9c33/image.png',
		font: '"Ember& Fire", sans-serif',
		primary: '#49B6F3',
		selected: '#F59E0B'
	},
    flagship: {
		logo: CampfireFlagship,
		background: 'https://cdn.hackclub.com/019c4e9a-2d12-728d-b2b1-a238ca90b7db/image.png',
		font: '"ADLaM Display", sans-serif',
		primary: '#000',
		selected: '#F59E0B'
    }
};

export type EventTheme = {
	logo: import('svelte').Component<any>;
	background: string;
	font: string;
	primary: string;
	selected: string;
};
