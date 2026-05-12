/**
 * seed-paragraph.ts
 * 
 * Builds the text production chain (bottom-up):
 *   Fragment → Sentence → Paragraph
 * 
 * Each level defines its ONTOLOGY only:
 *   - Fragment: terminal. 8 word classes with spectra. This is the bottom.
 *   - Sentence: subspace=Fragment. Digits select from Fragment's word classes.
 *              Dots would create sub-slots if Sentence had its own subspace below.
 *   - Paragraph: subspace=Sentence. Dots separate sentence slots.
 *              Each segment decodes through Sentence → Fragment.
 * 
 * The coordinate IS the thing. The number of slots comes from the coordinate,
 * not from hardcoded node counts.
 * 
 * Usage: npx tsx scripts/seed-paragraph.ts
 */

import { db } from '@/lib/db/drizzle';
import { spaces } from '@/lib/db/schema';
import { eq, and } from 'drizzle-orm';
import {
    createCrystalBall,
    addNode,

    attachSubspace,
    serialize,
    type CrystalBall,
} from '../lib/crystal-ball/index';

const TEAM_ID = 1;

// ─── Level 0: Fragment (Terminal) ─────────────────────────────────
// Word classes with their spectra. This is the bottom of the chain.
// No subspace — this is where selections terminate.

function buildFragment(): CrystalBall {
    const f = createCrystalBall('Fragment');

    // 7 word classes — the primacy spectrum of Fragment
    // (7 because digits 1-7 select directly, 8=drill, 9=wrap)
    const noun = addNode(f, 'root', 'Noun');
    const verb = addNode(f, 'root', 'Verb');
    const adj = addNode(f, 'root', 'Adjective');
    const adv = addNode(f, 'root', 'Adverb');
    const prep = addNode(f, 'root', 'Preposition');
    const conj = addNode(f, 'root', 'Conjunction');
    const det = addNode(f, 'root', 'Determiner');

    // Noun spectra

    // Verb spectra

    // Adjective spectra

    // Adverb spectra

    // Preposition spectra

    // Conjunction spectra

    // Determiner spectra

    return f;
}

// ─── Level 1: Sentence ───────────────────────────────────────────
// A sentence's subspace is Fragment. Each digit resolves through Fragment.
// No pre-created children — the coordinate defines word positions.

function buildSentence(fragment: CrystalBall): CrystalBall {
    const s = createCrystalBall('Sentence');

    // Root's subspace = Fragment. Digits in a Sentence coordinate
    // select from Fragment's word classes.
    attachSubspace(s, 'root', fragment);

    // Sentence-level attributes on root

    return s;
}

// ─── Level 2: Paragraph ──────────────────────────────────────────
// A paragraph's subspace is Sentence. Dots separate sentence slots.
// Each segment decodes through Sentence (which decodes through Fragment).

function buildParagraph(sentence: CrystalBall): CrystalBall {
    const p = createCrystalBall('Paragraph');

    // Root's subspace = Sentence. Each dot-separated segment
    // is a sentence slot, decoded through Sentence space.
    attachSubspace(p, 'root', sentence);

    // Paragraph-level attributes on root

    return p;
}

// ─── Main: Build and Insert ──────────────────────────────────────

async function main() {
    console.log('Building text production chain: Fragment → Sentence → Paragraph\n');

    // Build bottom-up
    const fragment = buildFragment();
    console.log(`✓ Fragment: ${fragment.nodes.size - 1} word classes (terminal)`);

    const sentence = buildSentence(fragment);
    console.log(`✓ Sentence: subspace=Fragment (digits select word classes)`);

    const paragraph = buildParagraph(sentence);
    console.log(`✓ Paragraph: subspace=Sentence (dots separate sentences)`);

    // Delete old spaces
    for (const name of ['Fragment', 'Sentence', 'Paragraph']) {
        await db.delete(spaces).where(
            and(eq(spaces.teamId, TEAM_ID), eq(spaces.name, name))
        );
    }
    console.log('\nCleared old spaces.');

    // Insert in dependency order (Fragment first, then Sentence, then Paragraph)
    for (const space of [fragment, sentence, paragraph]) {
        const serialized = serialize(space);
        await db.insert(spaces).values({
            teamId: TEAM_ID,
            name: space.name,
            data: serialized as any,
        });
    }

    console.log('Inserted: Fragment, Sentence, Paragraph');
    console.log('\nProduction chain ready. Coordinate IS the thing:');
    console.log('  Paragraph 12.34   → 2 sentences (12=Noun+Verb, 34=Adj+Adv)');
    console.log('  Paragraph 1       → 1 sentence (1=Noun)');
    console.log('  Paragraph 12.34.5 → 3 sentences');
    console.log('  Fragment 1        → Noun (terminal, backward compat)');

    process.exit(0);
}

main().catch(err => {
    console.error('Error:', err);
    process.exit(1);
});
