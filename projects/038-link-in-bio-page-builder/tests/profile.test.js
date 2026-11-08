import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { LIMITS, initials, moveItem, normalizeUrl, parseLinks, validateProfile, validateSlug } from '../src/lib/profile.js';
import { THEMES } from '../src/lib/themes.js';

describe('validateSlug', () => {
	it('normalizes case and whitespace', () => {
		expect(validateSlug('  Ada-Lovelace ')).toEqual({ ok: true, value: 'ada-lovelace' });
	});
	it.each(['ab', '-abc', 'abc-', 'a b c', 'ab/cd', '../etc', 'a'.repeat(31), '', null])('rejects %s', (slug) => {
		expect(validateSlug(slug).ok).toBe(false);
	});
	it('accepts the length boundaries', () => {
		expect(validateSlug('abc').ok).toBe(true);
		expect(validateSlug('a'.repeat(30)).ok).toBe(true);
	});
	it('rejects reserved words', () => {
		expect(validateSlug('edit').ok).toBe(false);
	});
});

describe('normalizeUrl', () => {
	it.each([
		['https://example.com/a?b=1', 'https://example.com/a?b=1'],
		['http://example.com', 'http://example.com/'],
		['example.com', 'https://example.com/'],
		['example.com:8080/x', 'https://example.com:8080/x'],
		['HTTPS://EXAMPLE.com', 'https://example.com/']
	])('accepts %s', (input, expected) => {
		expect(normalizeUrl(input)).toBe(expected);
	});

	it.each([
		'javascript:alert(1)',
		'JaVaScRiPt:alert(1)',
		' javascript:alert(1)',
		'java\nscript:alert(1)',
		'data:text/html,<script>alert(1)</script>',
		'vbscript:msgbox(1)',
		'file:///etc/passwd',
		'ftp://example.com',
		'https://bank.example@evil.test/',
		'notahost',
		'',
		null
	])('rejects %j', (input) => {
		expect(normalizeUrl(input)).toBeNull();
	});

	it('rejects overlong URLs', () => {
		expect(normalizeUrl(`https://example.com/${'a'.repeat(LIMITS.url)}`)).toBeNull();
	});
});

describe('validateProfile', () => {
	const valid = { displayName: ' Ada ', bio: 'Hi', theme: 'paper', links: [{ id: 'x', title: ' Site ', url: 'example.com' }] };

	it('trims and normalizes valid input', () => {
		expect(validateProfile(valid)).toEqual({
			ok: true,
			value: { displayName: 'Ada', bio: 'Hi', theme: 'paper', links: [{ id: 'x', title: 'Site', url: 'https://example.com/' }] }
		});
	});
	it('reports each bad field', () => {
		const result = validateProfile({ displayName: '  ', bio: 'x'.repeat(161), theme: 'nope', links: [{ title: '', url: 'javascript:alert(1)' }] });
		expect(Object.keys(result.errors).sort()).toEqual(['bio', 'displayName', 'links.0.title', 'links.0.url', 'theme']);
	});
	it('caps the number of links', () => {
		const links = Array.from({ length: LIMITS.links + 1 }, () => ({ title: 'a', url: 'example.com' }));
		expect(validateProfile({ ...valid, links }).errors.links).toMatch(/up to/);
	});
	it('counts characters, not UTF-16 units', () => {
		expect(validateProfile({ ...valid, displayName: '😀'.repeat(LIMITS.displayName) }).ok).toBe(true);
	});
	it('survives malformed link entries', () => {
		expect(validateProfile({ ...valid, links: [null, 7] }).ok).toBe(false);
	});
});

describe('helpers', () => {
	it('parseLinks only accepts JSON arrays', () => {
		expect(parseLinks('[{"a":1}]')).toEqual([{ a: 1 }]);
		expect(parseLinks('{"a":1}')).toBeNull();
		expect(parseLinks('not json')).toBeNull();
		expect(parseLinks(null)).toEqual([]);
	});
	it.each([['Ada Lovelace', 'AL'], ['ada', 'A'], ['Mary Ann Evans', 'ME'], ['😀 smile', '😀S'], ['   ', '?']])('initials(%j) = %s', (name, expected) => {
		expect(initials(name)).toBe(expected);
	});
	it('moveItem moves without mutating', () => {
		const input = ['a', 'b', 'c'];
		expect(moveItem(input, 0, 2)).toEqual(['b', 'c', 'a']);
		expect(input).toEqual(['a', 'b', 'c']);
	});
	it('moveItem ignores out-of-range moves', () => {
		expect(moveItem(['a', 'b'], 0, -1)).toEqual(['a', 'b']);
		expect(moveItem(['a', 'b'], 1, 2)).toEqual(['a', 'b']);
	});
	it('every theme has CSS', () => {
		const css = readFileSync(new URL('../src/app.css', import.meta.url), 'utf8');
		for (const { id } of THEMES) expect(css).toContain(`[data-theme='${id}']`);
	});
});
