#!/usr/bin/env python3
"""Odyssey organ standalone test.

Creates dummy GIINT concepts via direct Neo4j (bypasses daemon queue).
Calls organ.process() directly.
Verifies Odyssey_* output concepts were created.
Cleans up all test data.

Usage:
    python3 test_odyssey.py
    python3 test_odyssey.py --keep   # don't clean up (for inspection)
"""

import os
import sys
import json
from datetime import datetime

# Neo4j config
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://host.docker.internal:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

TEST_PREFIX = "Zzz_Test_Odyssey_"  # sorts last, easy to find and clean


def get_driver():
    from neo4j import GraphDatabase
    return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))


def create_test_concepts(driver):
    """Create a realistic dummy GIINT hierarchy for testing."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    names = {
        "project": f"{TEST_PREFIX}Project_{ts}",
        "feature": f"{TEST_PREFIX}Feature_{ts}",
        "component": f"{TEST_PREFIX}Component_{ts}",
        "deliverable": f"{TEST_PREFIX}Deliverable_{ts}",
        "task": f"{TEST_PREFIX}Task_{ts}",
        "inclusion_map": f"{TEST_PREFIX}Inclusion_Map_{ts}",
        "measurement": f"{TEST_PREFIX}Measurement_Analysis_{ts}",
        "learning": f"{TEST_PREFIX}Learning_Decision_{ts}",
        "bml_learning": f"{TEST_PREFIX}Bml_Learning_{ts}",
    }

    with driver.session() as s:
        # Create the hierarchy
        s.run("""
            CREATE (p:Wiki {n: $project, d: 'Test GIINT project for Odyssey', c: 'test', t: datetime()})
            CREATE (f:Wiki {n: $feature, d: 'Test feature', c: 'test', t: datetime()})
            CREATE (comp:Wiki {n: $component, d: 'Test component', c: 'test', t: datetime()})
            CREATE (del:Wiki {n: $deliverable, d: 'Test deliverable', c: 'test', t: datetime()})
            CREATE (task:Wiki {n: $task, d: 'Test task. DONE_SIGNAL: Changed test.py line 5, test_foo passes, output verified.', c: 'test', t: datetime()})
            CREATE (im:Wiki {n: $inclusion_map, d: 'PASS. Done signal has structural proof: file changed, test passed, output verified.', c: 'test', t: datetime()})
            CREATE (ma:Wiki {n: $measurement, d: 'Total: 1, PASS: 1, FAIL: 0. Recommendation: CONTINUE', c: 'test', t: datetime()})
            CREATE (ld:Wiki {n: $learning, d: 'Decision: CONTINUE. All inclusion maps passed.', c: 'test', t: datetime()})
            CREATE (bl:Wiki {n: $bml_learning, d: 'Learning complete — all Inclusion Maps passed, deliverable proven. TEST DATA.', c: 'test', t: datetime()})

            // IS_A relationships
            CREATE (p)-[:IS_A]->(:Wiki {n: 'GIINT_Project', c: 'giint_project'})
            CREATE (f)-[:IS_A]->(:Wiki {n: 'GIINT_Feature', c: 'giint_feature'})
            CREATE (comp)-[:IS_A]->(:Wiki {n: 'GIINT_Component', c: 'giint_component'})
            CREATE (del)-[:IS_A]->(:Wiki {n: 'GIINT_Deliverable', c: 'giint_deliverable'})
            CREATE (task)-[:IS_A]->(:Wiki {n: 'GIINT_Task', c: 'giint_task'})
            CREATE (im)-[:IS_A]->(:Wiki {n: 'Inclusion_Map', c: 'inclusion_map'})
            CREATE (ma)-[:IS_A]->(:Wiki {n: 'Measurement_Analysis', c: 'measurement_analysis'})
            CREATE (ld)-[:IS_A]->(:Wiki {n: 'Learning_Decision', c: 'learning_decision'})
            CREATE (bl)-[:IS_A]->(:Wiki {n: 'Bml_Learning', c: 'bml_learning'})

            // PART_OF hierarchy
            CREATE (f)-[:PART_OF]->(p)
            CREATE (comp)-[:PART_OF]->(f)
            CREATE (del)-[:PART_OF]->(comp)
            CREATE (task)-[:PART_OF]->(del)
            CREATE (im)-[:PART_OF]->(task)
            CREATE (ma)-[:PART_OF]->(del)
            CREATE (ld)-[:PART_OF]->(del)
            CREATE (bl)-[:PART_OF]->(task)
        """, **names)

    print(f"Created {len(names)} test concepts with prefix {TEST_PREFIX}")
    return names


def run_test(names):
    """Call organ.process() on the test Bml_Learning concept."""
    from odyssey import OdysseyOrgan

    organ = OdysseyOrgan()
    organ.start()

    concept_ref = names["bml_learning"]
    print(f"\nRunning organ.process('{concept_ref}')...")
    print("(This will spawn an SDNAC agent — takes ~30-60 seconds)\n")

    result = organ.process(concept_ref)

    print(f"\nResult:")
    print(f"  success: {result.success}")
    print(f"  event_type: {result.event_type}")
    print(f"  concept_ref: {result.concept_ref}")
    print(f"  concepts_created: {result.concepts_created}")
    print(f"  decision: {result.decision}")
    print(f"  error: {result.error}")

    return result


def verify_output(driver, result):
    """Check if Odyssey_* concepts were actually created in CartON."""
    print("\nVerifying output concepts in Neo4j...")
    found = []
    missing = []

    with driver.session() as s:
        for concept_name in result.concepts_created:
            r = s.run("MATCH (n:Wiki) WHERE n.n CONTAINS $name RETURN n.n, n.d",
                      name=concept_name.split("_")[-1])  # search by timestamp suffix
            records = list(r)
            if records:
                found.append(concept_name)
                print(f"  FOUND: {records[0]['n.n']}")
                print(f"    desc: {records[0]['n.d'][:100]}...")
            else:
                missing.append(concept_name)
                print(f"  MISSING: {concept_name}")

    if missing:
        print(f"\n FAIL: {len(missing)} expected concepts not found")
    else:
        print(f"\n PASS: All {len(found)} expected concepts created")

    return len(missing) == 0


def cleanup(driver):
    """Remove all test concepts."""
    with driver.session() as s:
        result = s.run(f"""
            MATCH (n:Wiki) WHERE n.n STARTS WITH '{TEST_PREFIX}'
            DETACH DELETE n
            RETURN count(n) as deleted
        """)
        deleted = result.single()["deleted"]
        print(f"\nCleaned up {deleted} test concepts")


def main():
    keep = "--keep" in sys.argv

    driver = get_driver()

    print("=" * 60)
    print("ODYSSEY ORGAN STANDALONE TEST")
    print("=" * 60)

    # 1. Create test data
    print("\n--- Step 1: Create test GIINT hierarchy ---")
    names = create_test_concepts(driver)

    # 2. Run the organ
    print("\n--- Step 2: Run organ.process() ---")
    try:
        result = run_test(names)
    except Exception as e:
        print(f"\n ORGAN ERROR: {e}")
        import traceback
        traceback.print_exc()
        if not keep:
            cleanup(driver)
        driver.close()
        sys.exit(1)

    # 3. Verify output
    print("\n--- Step 3: Verify output ---")
    passed = verify_output(driver, result)

    # 4. Cleanup
    if not keep:
        print("\n--- Step 4: Cleanup ---")
        cleanup(driver)
    else:
        print("\n--- Step 4: Skipped cleanup (--keep) ---")
        print(f"  Test concepts have prefix: {TEST_PREFIX}")

    driver.close()

    print("\n" + "=" * 60)
    if passed and result.success:
        print("TEST PASSED")
    else:
        print("TEST FAILED")
    print("=" * 60)

    sys.exit(0 if (passed and result.success) else 1)


if __name__ == "__main__":
    main()
