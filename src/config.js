export const BRAND = {
  name: "ARJUN",
  epithet: "The Astral Shield & Precision Engine",
  version: "2.6.0",
};

export const APP = {
  name: import.meta.env.VITE_APP_NAME || BRAND.name,
  tagline: import.meta.env.VITE_APP_TAGLINE || BRAND.epithet,
  entityLabel: import.meta.env.VITE_ENTITY_LABEL || 'File',
  entityPlural: import.meta.env.VITE_ENTITY_PLURAL || 'Files',
  categories: ['General', 'Education', 'Health', 'Civic', 'Agriculture', 'Safety', 'Fintech', 'Environment']
}
