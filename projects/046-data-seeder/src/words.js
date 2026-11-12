/**
 * Small built-in corpora. Kept deliberately compact so the project has zero
 * dependencies; extend them freely.
 */

export const FIRST_NAMES = [
  'Amara', 'Ben', 'Chen', 'Diego', 'Elena', 'Farah', 'Gabriel', 'Hana', 'Isaac', 'Jada',
  'Kenji', 'Layla', 'Mateo', 'Nadia', 'Omar', 'Priya', 'Quinn', 'Rosa', 'Samir', 'Tara',
  'Uma', 'Victor', 'Wren', 'Xavier', 'Yara', 'Zane', 'Aisha', 'Bruno', 'Clara', 'Dev',
];

export const LAST_NAMES = [
  'Adeyemi', 'Brooks', 'Castillo', 'Dubois', 'Eriksen', 'Fischer', 'Garcia', 'Hassan',
  'Ito', 'Johnson', 'Kowalski', 'Lee', 'Martinez', 'Nguyen', 'Okafor', 'Patel', 'Quintero',
  'Rossi', 'Schmidt', 'Tanaka', 'Usman', 'Vargas', 'Williams', 'Xu', 'Yilmaz', 'Zhang',
];

export const EMAIL_DOMAINS = ['example.com', 'example.org', 'example.net', 'test.dev'];

export const STREET_SUFFIXES = ['St', 'Ave', 'Blvd', 'Rd', 'Ln', 'Way', 'Ct', 'Pl'];
export const STREET_NAMES = [
  'Maple', 'Oak', 'Cedar', 'Pine', 'Elm', 'Lake', 'Hill', 'River', 'Park', 'Sunset',
  'Main', 'Church', 'Mill', 'Spring', 'Ridge', 'Willow',
];

export const CITIES = [
  'Springfield', 'Riverton', 'Fairview', 'Lakewood', 'Georgetown', 'Clinton', 'Franklin',
  'Madison', 'Ashland', 'Milton', 'Oakdale', 'Salem',
];

export const COUNTRIES = ['US', 'CA', 'GB', 'DE', 'FR', 'JP', 'BR', 'IN', 'NG', 'AU'];

export const COMPANY_PREFIXES = ['Blue', 'North', 'Bright', 'Iron', 'Silver', 'Green', 'Quantum', 'Rapid'];
export const COMPANY_NOUNS = ['Labs', 'Works', 'Systems', 'Logic', 'Dynamics', 'Foundry', 'Collective', 'Analytics'];

export const PRODUCT_ADJECTIVES = ['Ergonomic', 'Rustic', 'Sleek', 'Compact', 'Smart', 'Durable', 'Handmade', 'Vintage'];
export const PRODUCT_MATERIALS = ['Steel', 'Wooden', 'Cotton', 'Granite', 'Bamboo', 'Leather', 'Glass', 'Ceramic'];
export const PRODUCT_NOUNS = ['Chair', 'Lamp', 'Mug', 'Backpack', 'Keyboard', 'Notebook', 'Bottle', 'Desk'];

// Lorem-ipsum-ish vocabulary for sentences and paragraphs.
export const LOREM = (
  'lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod tempor ' +
  'incididunt ut labore et dolore magna aliqua enim ad minim veniam quis nostrud ' +
  'exercitation ullamco laboris nisi aliquip ex ea commodo consequat duis aute irure ' +
  'in reprehenderit voluptate velit esse cillum fugiat nulla pariatur excepteur sint ' +
  'occaecat cupidatat non proident sunt culpa qui officia deserunt mollit anim id est laborum'
).split(' ');
