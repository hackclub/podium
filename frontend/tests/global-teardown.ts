import { request } from '@playwright/test';

const API_BASE_URL = 'http://127.0.0.1:8000';

export default async function globalTeardown() {
	console.log('Cleaning up test data...');

	const api = await request.newContext({ baseURL: API_BASE_URL });

	try {
		const response = await api.post('/events/test/cleanup');
		if (response.ok()) {
			console.log('✅ Test data cleaned up successfully');
		} else {
			console.error(`⚠️ Cleanup failed: ${response.status()} ${await response.text()}`);
		}
	} catch (error) {
		console.error('⚠️ Cleanup request failed:', error);
	} finally {
		await api.dispose();
	}
}
