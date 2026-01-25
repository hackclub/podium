import type { Page, Locator } from '@playwright/test';

export async function waitForApiOk(
	page: Page,
	urlPartOrRegex: string | RegExp,
	method?: string,
	timeout = 15000
): Promise<void> {
	const res = await page.waitForResponse(
		(res) => {
			const url = res.url();
			const meth = res.request().method();
			const urlMatch =
				typeof urlPartOrRegex === 'string' ? url.includes(urlPartOrRegex) : urlPartOrRegex.test(url);
			const methodMatch = method ? meth === method : true;
			return urlMatch && methodMatch;
		},
		{ timeout }
	);
	if (!res.ok()) {
		const body = await res.text().catch(() => '');
		throw new Error(`API ${method ?? 'ANY'} ${res.url()} returned ${res.status()}: ${body.slice(0, 400)}`);
	}
}

export async function clickAndWaitForApi(
	page: Page,
	locator: Locator | string,
	urlPartOrRegex: string | RegExp,
	method = 'GET',
	timeout = 15000
): Promise<void> {
	const loc = typeof locator === 'string' ? page.locator(locator) : locator;
	await Promise.all([waitForApiOk(page, urlPartOrRegex, method, timeout), loc.click()]);
}
