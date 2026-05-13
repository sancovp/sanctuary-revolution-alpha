# YOUKNOW Test Triage — 2026-05-13

21 failing / 21 passing. Diagnostic map only. No fixes here. Stage 3 uses this as the warning library.

## Summary by category

| Category | Count | Action for Stage 3 |
|---|---|---|
| TIME_CAPSULE     | 2  | retire (Y-layer migrated to SOMA) |
| ASSERTION_OUTDATED | 12 | rewrite assertions to new SOUP wording / stricter gate |
| DEPRECATED_REFERENCE | 1  | repath to deprecated_owl/ or retire |
| LIKELY_REGRESSION | 5  | hallucination persistence path: wiring present, output not landing where tests look |
| SEMANTIC_SHIFT  | 1  | parse-failure→SOUP behavior change — verify intent |
| PREDICTOR (overlay) | 6 of the 12 above also double as PREDICTORS — see notes |

## Per-test map

### test_operational_wiring.py (2) — TIME_CAPSULE

- `test_controller_telemetry_tracks_threshold_for_programs_path` — `assert False is True` on controller telemetry. Whole concept depended on Y-layer routing + threshold/programs gate path. Retire.
- `test_controller_telemetry_stays_soup_for_unknown_claim` — line 47 `'y1' == 'y4'`. Asserts target_layer Y-strata routing. **Y-layer migrated to SOMA soma_y_mesh.pl 2026-04-06.** Python Y-layer path deprecated. Retire.

### test_promotion_gate.py (6) — ASSERTION_OUTDATED + PREDICTORS

All 6 expect either `result == "OK"` for fully-built entities or specific old SOUP wording strings (`'justifies coverage incomplete'`, `'MSC missing for target entity'`, `'programs threshold not reached'`, `'CatOfCat chain is not declared bounded'`). Current SOUP wording is `[Missing {for X: [part_of: where this belongs (containment)]}]`.

- `test_strong_compression_and_bounded_chain_admits_to_ont` — expects OK on TypedPass. **PREDICTOR**: Stage 3 admission of GIINT_Project_X must reach CODE/OK, not get stuck on part_of containment. Current gate rejects even fully-set-up entities.
- `test_missing_justifies_stays_in_soup` — wording update only.
- `test_missing_msc_stays_in_soup` — wording update only.
- `test_programs_false_stays_in_soup` — wording update only.
- `test_unbounded_chain_stays_in_soup` — wording update only.
- `test_ont_admission_calls_youknow_add_boundary` — expects OK + boundary call. **PREDICTOR**: Stage 3 must verify post-admission side effects fire.

### test_statement_predicates.py (3) — ASSERTION_OUTDATED + PREDICTORS

- `test_has_msc_node_triple_satisfies_msc_presence_gate` — expects OK, gets SOUP with `_to_be_ONT`. **PREDICTOR**: ONT layer not implemented (see EMR rule). Test asserts ONT-layer behavior.
- `test_catofcatbounded_triple_can_enable_bounded_gate_and_admission` — same. **PREDICTOR**: bounded-gate admission path.
- `test_rich_statement_can_admit_new_entity_without_preseeding` — same, plus `line_error` token. **PREDICTOR**: Stage 3 needs to know if rich statements can self-bootstrap an entity (currently no).

### test_soup_wiring.py (7) — mixed

- `test_soup_contains_unknown_marker` — ASSERTION_OUTDATED. New format uses `(unknown type)` not `Unknown:`.
- `test_soup_lists_broken_chains_for_all_statement_relations` — ASSERTION_OUTDATED. Same marker change.
- `test_soup_file_created` — **LIKELY_REGRESSION**. _persist_to_soup is wired (compiler.py:481, 547, 573) but soup dir is empty at test time. Either env-var/HEAVEN_DATA_DIR path mismatch in this test, or the SOUP branch returning before persistence in some cases.
- `test_hallucination_metadata_structure` — **LIKELY_REGRESSION**. Same root cause as above (IndexError on empty file list).
- `test_soup_persists_hallucination_to_domain_owl` — **LIKELY_REGRESSION**. PIOEntity triple not in domain.owl. uarl.owl still defines PIOEntity, _persist_soup_to_uarl_domain exists at compiler.py:2270. Wiring incomplete or not triggered.
- `test_soup_repl_calls_update_single_hallucination_node` — **LIKELY_REGRESSION**. `assert 0 == 1` on hallucination count in domain.owl. Same persistence path.
- `test_parse_failure_not_soup` — **SEMANTIC_SHIFT**. `assert not True` — parse-failure result is now flagged as SOUP. Verify intent: should genuine parse errors return WRONG not SOUP? Decision needed in Stage 3.

### test_uarl_pattern_typing.py (2)

- `test_uarl_foundation_contains_compression_and_boundedness_terms` — **DEPRECATED_REFERENCE**. Hardcoded path to `youknow_kernel/uarl_v3.owl`. File now at `deprecated_owl/uarl_v3.owl` (one dir up). Either repath or retire if v3 foundation no longer canonical (uarl.owl is the live one per canonical-source-dirs rule).
- `test_admitted_pattern_persists_strong_typing_to_domain_owl` — ASSERTION_OUTDATED. Expects OK on TypedPass admission; same shape as promotion_gate failures. **PREDICTOR**: Stage 3 admission must persist PatternOfIsA to domain.owl.

### test_witness_phase.py (1)

- `test_post_admission_witness_file_created` — ASSERTION_OUTDATED. Expects OK admission so the witness file gets written. Blocked on the same admission-path issue as promotion_gate tests. **PREDICTOR**: post-admission witness writing must fire.

## Stage 3 warning library

The 21 failures collapse into FOUR underlying questions Stage 3 will face:

1. **The part_of containment gate is rejecting everything.** 12 tests fail because fully-set-up entities (TypedPass, NoJustify with part_of=["YOUKNOW"], etc.) hit `[Missing {for X: [part_of: where this belongs (containment)]}]`. Stage 3 admitting GIINT_Project_X will hit this same wall. Triage points at compiler.py admission gate + system_type_validator part_of resolution.

2. **Hallucination/PIO domain.owl persistence is wired but not landing.** 4 tests show _persist_to_soup is called but soup files / PIOEntity triples don't appear in the expected locations. Stage 3 wants SOUP entries to land in CartON as Pattern_/Bug_ EC fallout — if local soup persistence is silently failing, the CartON path may be silently failing too.

3. **ONT-layer admission is unreachable.** 3 statement_predicate tests assert OK admission via rich-statement-triples bootstrap. EMR rule says ONT not implemented. Stage 3 should NOT try to push concepts to ONT — accept SYSTEM_TYPE admission as the ceiling.

4. **Y-layer dead code residue.** 2 tests still assert Y-layer routing. Y-layer is SOMA territory. Don't re-add Y-layer to OWLTypeRegistry — leave the call sites returning None/[] (already commented in core.py:223, 417, 421).

## Test list (verbatim, for grep)

```
FAILED tests/test_operational_wiring.py::test_controller_telemetry_tracks_threshold_for_programs_path  [TIME_CAPSULE]
FAILED tests/test_operational_wiring.py::test_controller_telemetry_stays_soup_for_unknown_claim         [TIME_CAPSULE]
FAILED tests/test_promotion_gate.py::test_strong_compression_and_bounded_chain_admits_to_ont            [ASSERTION_OUTDATED + PREDICTOR]
FAILED tests/test_promotion_gate.py::test_missing_justifies_stays_in_soup                                [ASSERTION_OUTDATED]
FAILED tests/test_promotion_gate.py::test_missing_msc_stays_in_soup                                      [ASSERTION_OUTDATED]
FAILED tests/test_promotion_gate.py::test_programs_false_stays_in_soup                                   [ASSERTION_OUTDATED]
FAILED tests/test_promotion_gate.py::test_unbounded_chain_stays_in_soup                                  [ASSERTION_OUTDATED]
FAILED tests/test_promotion_gate.py::test_ont_admission_calls_youknow_add_boundary                       [ASSERTION_OUTDATED + PREDICTOR]
FAILED tests/test_soup_wiring.py::TestSoupWiring::test_soup_contains_unknown_marker                      [ASSERTION_OUTDATED]
FAILED tests/test_soup_wiring.py::TestSoupWiring::test_soup_lists_broken_chains_for_all_statement_relations [ASSERTION_OUTDATED]
FAILED tests/test_soup_wiring.py::TestSoupWiring::test_soup_file_created                                 [LIKELY_REGRESSION]
FAILED tests/test_soup_wiring.py::TestSoupWiring::test_hallucination_metadata_structure                  [LIKELY_REGRESSION]
FAILED tests/test_soup_wiring.py::TestSoupWiring::test_soup_persists_hallucination_to_domain_owl         [LIKELY_REGRESSION]
FAILED tests/test_soup_wiring.py::TestSoupWiring::test_soup_repl_calls_update_single_hallucination_node  [LIKELY_REGRESSION]
FAILED tests/test_soup_wiring.py::TestSoupWiring::test_parse_failure_not_soup                            [SEMANTIC_SHIFT]
FAILED tests/test_statement_predicates.py::test_has_msc_node_triple_satisfies_msc_presence_gate          [ASSERTION_OUTDATED + PREDICTOR]
FAILED tests/test_statement_predicates.py::test_catofcatbounded_triple_can_enable_bounded_gate_and_admission [ASSERTION_OUTDATED + PREDICTOR]
FAILED tests/test_statement_predicates.py::test_rich_statement_can_admit_new_entity_without_preseeding   [ASSERTION_OUTDATED + PREDICTOR]
FAILED tests/test_uarl_pattern_typing.py::test_uarl_foundation_contains_compression_and_boundedness_terms [DEPRECATED_REFERENCE]
FAILED tests/test_uarl_pattern_typing.py::test_admitted_pattern_persists_strong_typing_to_domain_owl     [ASSERTION_OUTDATED + PREDICTOR]
FAILED tests/test_witness_phase.py::test_post_admission_witness_file_created                             [ASSERTION_OUTDATED + PREDICTOR]
```
