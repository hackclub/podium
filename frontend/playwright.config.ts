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
	globalTeardown: './tests/global-teardown.ts',

	webServer: isExternal ? undefined : [
		{
			command: 'cd .. && pnpm --filter podium-gateway dev',
			port: 3000,
			timeout: 120000,
			reuseExistingServer: true,
			stdout: 'pipe',
			stderr: 'pipe'
		},
		{
			command: 'cd ../packages/auth-service && pnpm start:dev',
			port: 8001,
			timeout: 120000,
			reuseExistingServer: true,
			stdout: 'pipe',
			stderr: 'pipe'
		},
		{
			command: 'cd ../packages/events-service && pnpm start:dev',
			port: 8002,
			timeout: 120000,
			reuseExistingServer: true,
			stdout: 'pipe',
			stderr: 'pipe'
		},
		{
			command: 'cd ../packages/projects-service && pnpm start:dev',
			port: 8003,
			timeout: 120000,
			reuseExistingServer: true,
			stdout: 'pipe',
			stderr: 'pipe'
		},
		{
			command: 'bun dev --port 4173',
			port: 4173,
			timeout: 120000,
			reuseExistingServer: true,
			env: {
				PUBLIC_API_URL: 'http://127.0.0.1:3000/api'
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
