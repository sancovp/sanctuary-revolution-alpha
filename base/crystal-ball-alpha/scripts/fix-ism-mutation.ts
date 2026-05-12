/**
 * One-shot fix: Remove accidentally-added nodes from IsaacsStoryMachine
 * - node "1.1" (TweetKernel under PublicIP) 
 * - node "97" (duplicate IsaacsStoryMachine under root)
 *
 * Run: npx tsx scripts/fix-ism-mutation.ts
 */
import { db } from '../lib/db/drizzle';
import { spaces } from '../lib/db/schema';
import { eq, and } from 'drizzle-orm';
import { deserialize, serialize, type SerializedCrystalBall } from '../lib/crystal-ball/index';

const TEAM_ID = 1;
const SPACE_NAME = 'IsaacsStoryMachine';

function removeChild(space: any, parentId: string, childId: string): boolean {
    const parent = space.nodes.get(parentId);
    if (!parent) return false;
    const idx = parent.children.indexOf(childId);
    if (idx < 0) return false;
    parent.children.splice(idx, 1);
    space.nodes.delete(childId);
    return true;
}

async function main() {
    const rows = await db
        .select()
        .from(spaces)
        .where(and(eq(spaces.teamId, TEAM_ID), eq(spaces.name, SPACE_NAME)));

    if (rows.length === 0) {
        console.log(`Space "${SPACE_NAME}" not found`);
        process.exit(1);
    }

    const rawData = rows[0].data as SerializedCrystalBall;
    const space = deserialize(rawData);

    const root = space.nodes.get('root')!;
    console.log(`Before: root has ${root.children.length} children: [${root.children.join(', ')}]`);

    let fixed = false;

    // Remove node "1.1" (TweetKernel under PublicIP)
    if (removeChild(space, '1', '1.1')) {
        console.log('Removed 1.1 (TweetKernel) from PublicIP');
        fixed = true;
    }

    // Remove node "97" (duplicate IsaacsStoryMachine under root)
    if (removeChild(space, 'root', '97')) {
        console.log('Removed 97 (duplicate IsaacsStoryMachine) from root');
        fixed = true;
    }

    if (!fixed) {
        console.log('Nothing to fix — already clean.');
        process.exit(0);
    }

    console.log(`After: root has ${root.children.length} children: [${root.children.join(', ')}]`);

    const serialized = serialize(space);
    await db
        .update(spaces)
        .set({ data: serialized as any, updatedAt: new Date() })
        .where(eq(spaces.id, rows[0].id));

    console.log('✅ Saved. ISM mutations fixed.');
    process.exit(0);
}

main().catch(err => {
    console.error(err);
    process.exit(1);
});
