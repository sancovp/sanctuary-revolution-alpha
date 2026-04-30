% Built-in story vocabulary. Shell input may also add arbitrary local predicates and rules.
authoring_predicate(story, 1).
authoring_predicate(target_depth, 2).
authoring_predicate(slot, 3).
authoring_predicate(edge, 3).
authoring_predicate(kv, 3).

builtin_key(theme).
builtin_key(grand_argument).
builtin_key(thesis).
builtin_key(trope).
builtin_key(scene).
builtin_key(framework).
builtin_key(genre).
builtin_key(story_engine).
builtin_key(internal_arc).
builtin_key(throughline).
builtin_key(scene_machine).
builtin_key(fresh_news).
builtin_key(hero_goal_engine).
builtin_key(thematic_truth).
builtin_key(catharsis).
builtin_key(template).
builtin_key(audience_experience).
builtin_key(story_quality).
builtin_key(observer_experience).
builtin_key(dark_night_branch).
builtin_key(real_world_symbols).
builtin_key(event).
builtin_key(dialogue).
builtin_key(character).

builtin_relation(about).
builtin_relation(supports).
builtin_relation(pressures).
builtin_relation(in_story).
builtin_relation(foundation_ref).
builtin_relation(leads_to).
builtin_relation(maps_to_beat).
builtin_relation(occurs_in).
builtin_relation(causes).
builtin_relation(tests).
builtin_relation(advances).
builtin_relation(reveals).
builtin_relation(revealed_in).
builtin_relation(presents).
builtin_relation(spoken_in).
builtin_relation(asserts).
builtin_relation(denies).
builtin_relation(reframes).
builtin_relation(deflects).
builtin_relation(baits).
builtin_relation(confesses).
builtin_relation(masks).
builtin_relation(because).
builtin_relation(objective).
builtin_relation(obstacle).
builtin_relation(turn).
builtin_relation(inherits_state_from).
builtin_relation(plays).
builtin_relation(pov).
builtin_relation(present_in).
builtin_relation(knows).
builtin_relation(conceals).
builtin_relation(speaker_knows).
builtin_relation(speaker_conceals).
builtin_relation(learns).
builtin_relation(plans).
builtin_relation(threatens).
builtin_relation(decides).
builtin_relation(fulfills).
builtin_relation(thwarts).
builtin_relation(inverts).
builtin_relation(echoes).
builtin_relation(costs).
builtin_relation(type).
builtin_relation(content_pattern).
builtin_relation(activated_by).
builtin_relation(reaches_for).
builtin_relation(escalates_toward).
builtin_relation(forced_by).
builtin_relation(enforced_by).
builtin_relation(signals).
builtin_relation(clings_to).
builtin_relation(exposes).
builtin_relation(redirects_toward).

max_cert_depth(theme, 4).
max_cert_depth(grand_argument, 4).
max_cert_depth(trope, 4).
max_cert_depth(scene, 12).
max_cert_depth(framework, 2).
max_cert_depth(genre, 3).
max_cert_depth(story_engine, 3).
max_cert_depth(internal_arc, 5).
max_cert_depth(throughline, 2).
max_cert_depth(scene_machine, 2).
max_cert_depth(fresh_news, 4).
max_cert_depth(hero_goal_engine, 3).
max_cert_depth(thematic_truth, 2).
max_cert_depth(catharsis, 3).
max_cert_depth(template, 4).
max_cert_depth(audience_experience, 3).
max_cert_depth(story_quality, 3).
max_cert_depth(observer_experience, 3).
max_cert_depth(dark_night_branch, 3).
max_cert_depth(real_world_symbols, 3).
max_cert_depth(event, 4).
max_cert_depth(dialogue, 14).
max_cert_depth(character, 3).

cert_step(theme, 1, theme_slot_present).
cert_step(theme, 2, theme_has_in_order_to_you_must_learn_form).
cert_step(theme, 3, theme_is_the_claim_proved_by_the_grand_argument).
cert_step(theme, 4, theme_is_proved_by_scene_instantiated_premises).

cert_step(grand_argument, 1, grand_argument_slot_present).
cert_step(grand_argument, 2, grand_argument_has_theme_and_thesis_chain).
cert_step(grand_argument, 3, grand_argument_contains_arguments_and_premises).
cert_step(grand_argument, 4, grand_argument_premises_are_instantiated_by_scenes).

cert_step(trope, 1, trope_slot_present).
cert_step(trope, 2, trope_supports_story_premise).
cert_step(trope, 3, trope_supports_theme_thesis_chain).
cert_step(trope, 4, trope_support_chain_is_pressured).

cert_step(scene, 1, scene_is_in_story).
cert_step(scene, 2, scene_inherits_story_scene_machine).
cert_step(scene, 3, scene_has_bridging_in_and_intention_initial_direction).
cert_step(scene, 4, scene_has_conflict_and_exposition).
cert_step(scene, 5, scene_has_characterization_climax_and_follow_up_bridging_out).
cert_step(scene, 6, scene_has_action_commitment).
cert_step(scene, 7, scene_action_respects_pov_knowledge).
cert_step(scene, 8, scene_type_functions_have_required_phase_entities).
cert_step(scene, 9, scene_type_functions_have_required_phase_relations).
cert_step(scene, 10, scene_type_functions_have_required_content_patterns).
cert_step(scene, 11, scene_content_patterns_have_required_internal_entities).
cert_step(scene, 12, scene_content_patterns_have_required_internal_relations).
cert_step(framework, 1, framework_slot_present).
cert_step(framework, 2, framework_resolves_to_story_machine_framework).
cert_step(genre, 1, genre_slot_present).
cert_step(genre, 2, genre_resolves_to_foundation_genre).
cert_step(genre, 3, genre_is_catalogued).
cert_step(story_engine, 1, story_engine_slot_present).
cert_step(story_engine, 2, story_engine_resolves_to_foundation_engine).
cert_step(story_engine, 3, story_engine_exposes_required_components).
cert_step(internal_arc, 1, internal_arc_slot_present).
cert_step(internal_arc, 2, internal_arc_resolves_to_engine).
cert_step(internal_arc, 3, internal_arc_tracks_lie_truth_shield).
cert_step(internal_arc, 4, internal_arc_progresses_through_capability_chain).
cert_step(internal_arc, 5, internal_arc_contains_dark_night_branch_logic).
cert_step(throughline, 1, throughline_slot_present).
cert_step(throughline, 2, throughline_resolves_to_complete_dramatica_cluster).
cert_step(scene_machine, 1, scene_machine_slot_present).
cert_step(scene_machine, 2, scene_machine_resolves_to_foundation_machine).
cert_step(fresh_news, 1, fresh_news_slot_present).
cert_step(fresh_news, 2, fresh_news_resolves_to_boundary_node).
cert_step(fresh_news, 3, fresh_news_has_hgs_boundary).
cert_step(fresh_news, 4, fresh_news_has_stc_boundary).
cert_step(hero_goal_engine, 1, hero_goal_engine_slot_present).
cert_step(hero_goal_engine, 2, hero_goal_engine_resolves_to_foundation_engine).
cert_step(hero_goal_engine, 3, hero_goal_engine_maps_to_sequence_and_plot_engines).
cert_step(thematic_truth, 1, thematic_truth_slot_present).
cert_step(thematic_truth, 2, thematic_truth_resolves_to_foundation_truth).
cert_step(catharsis, 1, catharsis_slot_present).
cert_step(catharsis, 2, catharsis_resolves_to_foundation_catharsis).
cert_step(catharsis, 3, catharsis_reflects_story_truth).
cert_step(template, 1, template_slot_present).
cert_step(template, 2, template_resolves_to_foundation_template).
cert_step(template, 3, template_has_structure_chain).
cert_step(template, 4, template_instantiates_tropes_and_aligns_with_myth).
cert_step(audience_experience, 1, audience_experience_slot_present).
cert_step(audience_experience, 2, audience_experience_resolves_to_foundation_audience_experience).
cert_step(audience_experience, 3, audience_experience_culminates_in_story_catharsis).
cert_step(story_quality, 1, story_quality_slot_present).
cert_step(story_quality, 2, story_quality_resolves_to_foundation_quality_node).
cert_step(story_quality, 3, story_quality_validates_story_template).
cert_step(observer_experience, 1, observer_experience_slot_present).
cert_step(observer_experience, 2, observer_experience_resolves_to_foundation_observer_experience).
cert_step(observer_experience, 3, observer_experience_is_shaped_and_drives_audience_experience).
cert_step(dark_night_branch, 1, dark_night_branch_slot_present).
cert_step(dark_night_branch, 2, dark_night_branch_resolves_to_comedy_or_tragedy_branch).
cert_step(dark_night_branch, 3, dark_night_branch_affects_story_quality).
cert_step(real_world_symbols, 1, real_world_symbols_slot_present).
cert_step(real_world_symbols, 2, real_world_symbols_resolves_to_foundation_symbol_system).
cert_step(real_world_symbols, 3, real_world_symbols_shape_story_observer_experience).
cert_step(event, 1, event_slot_present).
cert_step(event, 2, event_occurs_in_certified_scene).
cert_step(event, 3, event_participates_in_causal_chain).
cert_step(event, 4, event_links_back_to_story_argument).
cert_step(dialogue, 1, dialogue_slot_present).
cert_step(dialogue, 2, dialogue_occurs_in_scene).
cert_step(dialogue, 3, dialogue_has_speaker_and_text).
cert_step(dialogue, 4, dialogue_has_rhetorical_stance).
cert_step(dialogue, 5, dialogue_aligns_with_scene_argument_surface).
cert_step(dialogue, 6, dialogue_has_canonical_character_state).
cert_step(dialogue, 7, dialogue_state_is_legibly_caused_by_scene_pressure).
cert_step(dialogue, 8, dialogue_has_scene_event_knowledge_binding).
cert_step(dialogue, 9, dialogue_respects_scene_concealment).
cert_step(dialogue, 10, dialogue_has_speaker_event_knowledge_binding).
cert_step(dialogue, 11, dialogue_surface_and_speaker_knowledge_form_valid_subtext).
cert_step(dialogue, 12, dialogue_speaker_knowledge_has_epistemic_lineage).
cert_step(dialogue, 13, dialogue_has_action_commitment).
cert_step(dialogue, 14, dialogue_action_respects_epistemic_state).
cert_step(character, 1, character_slot_present).
cert_step(character, 2, character_has_story_role).
cert_step(character, 3, character_is_anchored_in_scene_surface).

required_role(story_compile, grand_argument, 1, 4).
required_role(story_compile, theme, 1, 4).
required_role(story_compile, trope, 1, 4).
required_role(story_compile, scene, 1, 1).
required_role(story_compile, scene, 8, 5).
required_role(story_compile, scene, 30, 7).
required_role(story_compile, scene, 33, 8).
required_role(story_compile, scene, 34, 9).
required_role(story_compile, scene, 35, 10).
required_role(story_compile, scene, 36, 11).
required_role(story_compile, scene, 37, 12).
required_role(story_compile, framework, 5, 2).
required_role(story_compile, genre, 5, 3).
required_role(story_compile, story_engine, 6, 3).
required_role(story_compile, internal_arc, 6, 5).
required_role(story_compile, throughline, 7, 2).
required_role(story_compile, scene_machine, 8, 2).
required_role(story_compile, fresh_news, 8, 4).
required_role(story_compile, hero_goal_engine, 8, 3).
required_role(story_compile, thematic_truth, 9, 2).
required_role(story_compile, catharsis, 9, 3).
required_role(story_compile, template, 10, 4).
required_role(story_compile, audience_experience, 10, 3).
required_role(story_compile, story_quality, 11, 3).
required_role(story_compile, observer_experience, 12, 3).
required_role(story_compile, dark_night_branch, 12, 3).
required_role(story_compile, real_world_symbols, 13, 3).
required_role(story_compile, event, 17, 4).
required_role(story_compile, dialogue, 20, 5).
required_role(story_compile, dialogue, 21, 7).
required_role(story_compile, dialogue, 26, 9).
required_role(story_compile, dialogue, 27, 11).
required_role(story_compile, dialogue, 28, 12).
required_role(story_compile, dialogue, 29, 14).
required_role(story_compile, character, 24, 3).
