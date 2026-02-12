// export const events = [
//     { event: 'campfire', satellite: 'Shelburne', slug: 'campfire-shelburne' },
//     { event: 'campfire', satellite: 'Burlington', slug: 'campfire-burlington' },
//     { event: 'flagship', slug: 'campfire-flagship' }
// ];
export const events: Record<string, EventData> = {
    'campfire-flagship': { theme: 'flagship', friendlyName: 'Flagship' },
    'campfire-shelburne': { theme: 'campfire', satellite: 'Shelburne', friendlyName: 'Shelburne' },
    'campfire-burlington': { theme: 'campfire', satellite: 'Burlington', friendlyName: 'Burlington' }
}

export type EventData = {
    theme: string;
    satellite?: string;
    friendlyName: string;
}

export const projects = [
	{ id: '1', name: 'Title', description: 'Description', image: '', demoUrl: '', repoUrl: '' },
	{ id: '2', name: 'Title', description: 'Description', image: '', demoUrl: '', repoUrl: '' },
	{ id: '3', name: 'Title', description: 'Description', image: '', demoUrl: '', repoUrl: '' },
	{ id: '4', name: 'Title', description: 'Description', image: '', demoUrl: '', repoUrl: '' },
	{ id: '5', name: 'Title', description: 'Description', image: '', demoUrl: '', repoUrl: '' },
	{ id: '6', name: 'Title', description: 'Description', image: '', demoUrl: '', repoUrl: '' },
	{ id: '7', name: 'Title', description: 'Description', image: '', demoUrl: '', repoUrl: '' },
	{ id: '8', name: 'Title', description: 'Description', image: '', demoUrl: '', repoUrl: '' },
	{ id: '9', name: 'Title', description: 'Description', image: '', demoUrl: '', repoUrl: '' },
	{ id: '10', name: 'Title', description: 'Description', image: '', demoUrl: '', repoUrl: '' },
	{ id: '11', name: 'Title', description: 'Description', image: '', demoUrl: '', repoUrl: '' },
];