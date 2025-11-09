import { defineConfig, devices } from '@playwright/test';

const externalBaseURL = process.env.PLAYWRIGHT_BASE_URL;
const isExternal = !!externalBaseURL;

export default defineConfig({
	testDir: './tests',
	fullyParallel: true,
	forbidOnly: !!process.env.CI,
	retries: process.env.CI ? 1 : 0,
	workers: 4,
	reporter: [
		['list'],
		['html', { outputFolder: 'playwright-report', open: 'never' }],
		['json', { outputFile: 'test-results.json' }]
	],
	timeout: 60000,

	use: {
		baseURL: externalBaseURL ?? 'http://127.0.0.1:4173',
		trace: 'on-first-retry',
		screenshot: 'only-on-failure',
		serviceWorkers: 'block',
		extraHTTPHeaders: {
			'Cache-Control': 'no-store',
			Pragma: 'no-cache'
		},
		expect: {
			timeout: 10000
		},
		actionTimeout: 15000,
		navigationTimeout: 30000
	},

	globalSetup: './tests/global-setup.ts',

	webServer: isExternal ? undefined : [
		{
			command: 'cd ../backend && uv run podium',
			port: 8000,
			timeout: 120000,
			reuseExistingServer: true
		},
		{
			command: 'bun dev --port 4173',
			port: 4173,
			timeout: 120000,
			reuseExistingServer: true
		}
	],

	projects: [
		{
			name: 'chromium',
			use: { ...devices['Desktop Chrome'] }
		}
	]
});
