import { createHash, randomBytes } from 'node:crypto';

/** 192 random bits: the edit link is the credential, so it must be unguessable. */
export function createEditToken() {
	return randomBytes(24).toString('base64url');
}

/**
 * Only the hash is stored, so a leaked data file does not expose edit links.
 * A fast hash is fine here because the input is high-entropy, unlike a password.
 * @param {string} token
 */
export function hashToken(token) {
	return createHash('sha256').update(token).digest('hex');
}
