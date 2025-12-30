import { defineConfig, devices } from '@playwright/test';

const externalBaseURL = process.env.PLAYWRIGHT_BASE_URL;
const isExternal = !!externalBaseURL;

export default defineConfig({
	testDir: './tests',
	fullyParallel: true,
	forbidOnly: !!process.env.CI,
	retries: process.env.CI ? 2 : 1,
	workers: 4,
	reporter: [
		['list', { printSteps: false }],
		['html', { outputFolder: 'playwright-report', open: 'never' }]
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
			// Backend runs with Doppler for secrets management
			// Use --preserve-env to allow CI to override PODIUM_DATABASE_URL
			command: 'cd ../backend && doppler run --project podium --config dev --preserve-env=PODIUM_DATABASE_URL -- uv run podium --log-level warning',
			port: 8000,
			timeout: 120000,
			reuseExistingServer: true,
			stdout: 'pipe',
			stderr: 'pipe',
			env: {
				PYTHONIOENCODING: 'utf-8',
				PYTHONWARNINGS: 'ignore',
				// Pass through PODIUM_DATABASE_URL if set (for CI)
				...(process.env.PODIUM_DATABASE_URL && { PODIUM_DATABASE_URL: process.env.PODIUM_DATABASE_URL })
			}
		},
		{
			// Use dev server (preview has CORS issues with client auth headers)
			command: 'bun dev --port 4173',
			port: 4173,
			timeout: 120000,
			reuseExistingServer: true,
			env: {
				PUBLIC_API_URL: 'http://127.0.0.1:8000'
			}
		}
	],

	projects: [
		{
			name: 'chromium',
			use: { ...devices['Desktop Chrome'] }
		}
	]
});
