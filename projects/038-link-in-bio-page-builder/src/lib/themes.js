/** Theme ids must each have a matching [data-theme] block in src/app.css. */
export const THEMES = [
	{ id: 'paper', label: 'Paper' },
	{ id: 'midnight', label: 'Midnight' },
	{ id: 'forest', label: 'Forest' },
	{ id: 'sunset', label: 'Sunset' }
];

export const DEFAULT_THEME = THEMES[0].id;
