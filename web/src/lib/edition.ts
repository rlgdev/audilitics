// One app, two builds (spec 7, 7.5). VITE_EDITION is replaced at build time, so the private routes and their
// imports are removed from the public bundle by dead-code elimination.
export type Edition = 'public' | 'private';

export const EDITION: Edition = import.meta.env.VITE_EDITION === 'private' ? 'private' : 'public';
export const IS_PRIVATE = EDITION === 'private';
