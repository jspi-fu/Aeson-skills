import { imgbb } from './imgbb.mjs';
import { freeimage } from './freeimage.mjs';
import { uploadme } from './uploadme.mjs';
import { imglink } from './imglink.mjs';

export const PROVIDERS = {
  imgbb,
  freeimage,
  uploadme,
  imglink
};

/**
 * Gets a provider instance by name.
 * 
 * @param {string} name - The provider key
 * @returns {object|undefined}
 */
export function getProvider(name) {
  return PROVIDERS[name.toLowerCase()];
}

/**
 * Lists all registered providers.
 * 
 * @returns {Array<object>}
 */
export function listProviders() {
  return Object.values(PROVIDERS);
}
