// export const events = [
//     { event: 'campfire', satellite: 'Shelburne', slug: 'campfire-shelburne' },
//     { event: 'campfire', satellite: 'Burlington', slug: 'campfire-burlington' },
//     { event: 'flagship', slug: 'campfire-flagship' }
// ];
export const events: Record<string, EventData> = {
    'campfire-flagship': { theme: 'flagship' },
    'campfire-shelburne': { theme: 'campfire', satellite: 'Shelburne' },
    'campfire-burlington': { theme: 'campfire', satellite: 'Burlington' }
}

export type EventData = {
    theme: string;
    satellite?: string;
}