import { mkdirSync } from 'fs';

export default async function globalSetup() {
	// Create .auth directory if it doesn't exist
	mkdirSync('.auth', { recursive: true });

	console.log('Global setup completed - auth directory created');
	
	// Verify JWT secret is available
	if (!process.env.PODIUM_JWT_SECRET) {
		console.error('❌ PODIUM_JWT_SECRET not found in environment');
		console.error('Available env vars:', Object.keys(process.env).filter(k => k.includes('PODIUM')));
		throw new Error('PODIUM_JWT_SECRET is required for tests');
	} else {
		console.log('✅ PODIUM_JWT_SECRET is available');
	}
}
