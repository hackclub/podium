import jwt from 'jsonwebtoken';

const JWT_SECRET = process.env.PODIUM_JWT_SECRET;
const JWT_ALGORITHM = 'HS256';

if (!JWT_SECRET) {
	throw new Error('PODIUM_JWT_SECRET environment variable is required for tests');
}

export function signMagicLinkToken(email: string, minutes = 15): string {
	const exp = Math.floor(Date.now() / 1000) + minutes * 60;
	return jwt.sign({ sub: email, token_type: 'magic_link', exp }, JWT_SECRET, {
		algorithm: JWT_ALGORITHM
	});
}

export function signAccessToken(email: string, minutes = 60): string {
	const exp = Math.floor(Date.now() / 1000) + minutes * 60;
	return jwt.sign({ sub: email, token_type: 'access', exp }, JWT_SECRET, {
		algorithm: JWT_ALGORITHM
	});
}
