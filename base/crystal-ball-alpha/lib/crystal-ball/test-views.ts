/**
 * Tags & Views test — different views of the same space produce different symmetry groups
 */
import {
    createRegistry, createSpace, addNode, lockNode,
    addTag, removeTag, hasTag, getNodesWithTag, getAllTags,
    createView, nodePassesView, getViewChildren,
    serialize, deserialize,
    type SpaceView,
} from './index';
import { computeMinePlane } from './mine';

let passed = 0;
let failed = 0;

function assert(condition: boolean, msg: string) {
    if (condition) {
        passed++;
        console.log(`  ✅ ${msg}`);
    } else {
        failed++;
        console.log(`  ❌ ${msg}`);
    }
}

// ═══ Build a space with 5 genres ═══
console.log('═══ TEST: Tags & Views ═══\n');

const registry = createRegistry();
const space = createSpace(registry, 'Movies');
const root = space.nodes.get('root')!;

const action = addNode(space, 'root', 'Action');
const comedy = addNode(space, 'root', 'Comedy');
const horror = addNode(space, 'root', 'Horror');
const romance = addNode(space, 'root', 'Romance');
const documentary = addNode(space, 'root', 'Documentary');

// Add sub-genres so we can lock
addNode(space, action.id, 'Martial_Arts');
addNode(space, action.id, 'Spy');
addNode(space, comedy.id, 'Slapstick');
addNode(space, comedy.id, 'Satirical');
addNode(space, horror.id, 'Slasher');
addNode(space, horror.id, 'Psychological');
addNode(space, romance.id, 'RomCom');
addNode(space, romance.id, 'Period_Drama');
addNode(space, documentary.id, 'Science');
addNode(space, documentary.id, 'History');

// ═══ Tag Operations ═══
console.log('Tag Operations:');

addTag(space, horror.id, 'blacklist');
assert(hasTag(space, horror.id, 'blacklist'), 'Horror is blacklisted');
assert(!hasTag(space, action.id, 'blacklist'), 'Action is NOT blacklisted');

addTag(space, action.id, 'favorites');
addTag(space, documentary.id, 'favorites');
assert(hasTag(space, action.id, 'favorites'), 'Action is favorited');

const blacklisted = getNodesWithTag(space, 'blacklist');
assert(blacklisted.length === 1, `1 blacklisted node (got ${blacklisted.length})`);
assert(blacklisted[0].label === 'Horror', 'Blacklisted node is Horror');

const favorites = getNodesWithTag(space, 'favorites');
assert(favorites.length === 2, `2 favorited nodes (got ${favorites.length})`);

const allTags = getAllTags(space);
assert(allTags.has('blacklist'), 'Tag set contains blacklist');
assert(allTags.has('favorites'), 'Tag set contains favorites');
assert(allTags.size === 2, `2 distinct tags (got ${allTags.size})`);

removeTag(space, horror.id, 'blacklist');
assert(!hasTag(space, horror.id, 'blacklist'), 'Horror un-blacklisted');

// Re-add for view tests
addTag(space, horror.id, 'blacklist');

// ═══ View Filtering ═══
console.log('\nView Filtering:');

const allView = createView('Everything');
const excludeBlacklist = createView('My Preferences', 'exclude_tagged', ['blacklist']);
const favoritesOnly = createView('Curated', 'include_tagged_only', ['favorites']);
const blacklistOnly = createView('What I Avoid', 'tagged_only', ['blacklist']);

// All view — everything passes
const allChildren = getViewChildren(space, 'root', allView);
assert(allChildren.length === 5, `All view: 5 children (got ${allChildren.length})`);

// Exclude blacklist — Horror excluded
const prefChildren = getViewChildren(space, 'root', excludeBlacklist);
assert(prefChildren.length === 4, `Exclude blacklist: 4 children (got ${prefChildren.length})`);
assert(!prefChildren.includes(horror.id), 'Horror excluded from preferences');

// Favorites only — Action, Documentary
const favChildren = getViewChildren(space, 'root', favoritesOnly);
assert(favChildren.length === 2, `Favorites only: 2 children (got ${favChildren.length})`);
assert(favChildren.includes(action.id), 'Action in favorites');
assert(favChildren.includes(documentary.id), 'Documentary in favorites');

// Blacklist only — Horror
const blChildren = getViewChildren(space, 'root', blacklistOnly);
assert(blChildren.length === 1, `Blacklist only: 1 child (got ${blChildren.length})`);
assert(blChildren.includes(horror.id), 'Horror in blacklist view');

// No view (undefined) — everything passes
const noViewChildren = getViewChildren(space, 'root');
assert(noViewChildren.length === 5, `No view: 5 children (got ${noViewChildren.length})`);

// ═══ Mining with Views ═══
console.log('\nMining with Views:');

// Mark all as terminal so we can mine without locking
root.terminal = true;

// Mine everything
const allMine = computeMinePlane(registry, 'Movies', '0', 2000, undefined);
assert(allMine.totalPaths === 15, `All mine: 15 paths (got ${allMine.totalPaths})`);

// Mine excluding blacklist (Horror and its 2 children excluded)
const prefMine = computeMinePlane(registry, 'Movies', '0', 2000, undefined, excludeBlacklist);
assert(prefMine.totalPaths === 12, `Exclude blacklist: 12 paths (got ${prefMine.totalPaths})`);

// Mine favorites only (Action + Documentary + their 4 children)
const favMine = computeMinePlane(registry, 'Movies', '0', 2000, undefined, favoritesOnly);
assert(favMine.totalPaths === 6, `Favorites only: 6 paths (got ${favMine.totalPaths})`);

// Mine blacklist only (Horror + its 2 children)
const blMine = computeMinePlane(registry, 'Movies', '0', 2000, undefined, blacklistOnly);
assert(blMine.totalPaths === 3, `Blacklist only: 3 paths (got ${blMine.totalPaths})`);

// ═══ Serialization ═══
console.log('\nSerialization:');

const serialized = serialize(space);
const horrorSerialized = serialized.nodes.find(n => n.id === horror.id);
assert(!!horrorSerialized?.tags, 'Tags serialized');
assert(horrorSerialized?.tags?.includes('blacklist') ?? false, 'Blacklist tag in serialized data');

const deserialized = deserialize(serialized);
const horrorDeserialized = deserialized.nodes.get(horror.id);
assert(horrorDeserialized?.tags?.has('blacklist') ?? false, 'Blacklist tag survives deserialization');

const actionDeserialized = deserialized.nodes.get(action.id);
assert(actionDeserialized?.tags?.has('favorites') ?? false, 'Favorites tag survives deserialization');

// Nodes without tags don't get empty sets
const comedyDeserialized = deserialized.nodes.get(comedy.id);
assert(comedyDeserialized?.tags === undefined, 'Untagged nodes have no tags Set');

// ═══ Summary ═══
console.log(`\n═══════════════════════════════════════`);
console.log(`  PASSED: ${passed}`);
console.log(`  FAILED: ${failed}`);
console.log(`  TOTAL:  ${passed + failed}`);
console.log(`═══════════════════════════════════════`);
process.exit(failed > 0 ? 1 : 0);
