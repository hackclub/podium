import { mkdirSync } from 'fs';

export default async function globalSetup() {
	// Create .auth directory if it doesn't exist
	mkdirSync('.auth', { recursive: true });

	console.log('Global setup completed - auth directory created');
}
