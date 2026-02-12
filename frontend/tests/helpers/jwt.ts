import jwt from 'jsonwebtoken';

const JWT_ALGORITHM = 'HS256' as const;

function getSecret(): string {
	const secret = process.env.PODIUM_JWT_SECRET;
	if (!secret) {
		throw new Error('PODIUM_JWT_SECRET environment variable is required for tests');
	}
	return secret;
}

export function signMagicLinkToken(email: string, minutes = 15): string {
	const exp = Math.floor(Date.now() / 1000) + minutes * 60;
	return jwt.sign({ sub: email, token_type: 'magic_link', exp }, getSecret(), {
		algorithm: JWT_ALGORITHM
	});
}

export function signAccessToken(email: string, minutes = 60): string {
	const exp = Math.floor(Date.now() / 1000) + minutes * 60;
	return jwt.sign({ sub: email, token_type: 'access', exp }, getSecret(), {
		algorithm: JWT_ALGORITHM
	});
}
