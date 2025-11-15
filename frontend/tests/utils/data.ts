import { TestInfo } from '@playwright/test';

export function unique(base: string, info: TestInfo): string {
	return `${base} ${Date.now()}-w${info.workerIndex}-r${info.retry}`;
}
