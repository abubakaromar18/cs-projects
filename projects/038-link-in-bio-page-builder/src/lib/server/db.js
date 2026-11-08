import { createStore } from './store.js';

/** The application's single store. DATA_FILE lets deployments and tests relocate it. */
export const db = createStore(process.env.DATA_FILE ?? 'data/pages.json');
