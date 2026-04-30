"""GAS Bridge — Pydantic → Prolog serializer for narrative validation.

Converts odyssey narrative models to GAS Prolog facts (slot/edge/kv triples).
The narrative SDNAC agent uses this to feed scenes to GAS for certification.

V1: Dual storage — GAS .pl files for narrative truth, CartON concepts for system queries.
Future: SOMA+GAS+YOUKNOW collapses dual storage.

Usage:
    from odyssey.gas_bridge import serialize_episode, serialize_twi, serialize_dialog

    # Serialize an episode to Prolog facts
    prolog_text = serialize_episode(episode_arc, twi, dialogs)

    # Write to workspace file
    Path("/tmp/heaven_data/gas_workspaces/episode_xyz.pl").write_text(prolog_text)

    # Feed to GAS for validation
    from ghost_story_bootstrap.harness import evaluate_submission
    result = evaluate_submission(workspace_path, foundation_path=GAS_FOUNDATION)
"""

import re
from typing import List, Optional
from datetime import datetime


# GAS foundation path
GAS_FOUNDATION = "/tmp/gas_v1_extracted/gas_bootstrap_depth_system/foundation.pl"
GAS_WORKSPACE_DIR = "/tmp/heaven_data/gas_workspaces"


def _to_atom(s: str) -> str:
    """Convert a string to a valid Prolog atom (lowercase, underscores, no spaces)."""
    if not s:
        return "unnamed"
    # Lowercase, replace non-alphanum with underscore, collapse multiples
    atom = re.sub(r'[^a-z0-9_]', '_', s.lower())
    atom = re.sub(r'_+', '_', atom).strip('_')
    # Prolog atoms can't start with a digit
    if atom and atom[0].isdigit():
        atom = 'n' + atom
    return atom or "unnamed"


def _quote_atom(s: str) -> str:
    """Quote a string as a Prolog atom (single quotes for strings with spaces/special chars)."""
    clean = s.replace("'", "\\'").replace("\n", " ")
    return f"'{clean}'"


def serialize_twi(story_atom: str, twi_id: str, in_order_to: str, learn_to_truly: str) -> str:
    """Serialize a TWI as GAS theme + thesis + grand_argument structure.

    Produces the minimum viable theme proof chain:
    theme → thesis → grand_argument → argument → premise
    """
    theme_atom = _to_atom(twi_id)
    thesis_atom = f"thesis_{theme_atom}"
    ga_atom = f"ga_{theme_atom}"
    arg_atom = f"arg_{theme_atom}"
    premise_atom = f"premise_{theme_atom}"

    lines = [
        f"% === Theme from TWI: {twi_id} ===",
        f"slot({story_atom}, theme, {theme_atom}).",
        f"kv({theme_atom}, in_order_to, {_quote_atom(in_order_to)}).",
        f"kv({theme_atom}, learn_to_truly, {_quote_atom(learn_to_truly)}).",
        "",
        f"% Grand argument proof chain",
        f"slot({story_atom}, thesis, {thesis_atom}).",
        f"edge({thesis_atom}, about, {theme_atom}).",
        f"slot({story_atom}, grand_argument, {ga_atom}).",
        f"edge({ga_atom}, thesis, {thesis_atom}).",
        f"edge({ga_atom}, proves, {theme_atom}).",
        "",
        f"% Argument and premise (agent fills with specifics)",
        f"edge({arg_atom}, part_of, {ga_atom}).",
        f"edge({arg_atom}, argues, {thesis_atom}).",
        f"edge({premise_atom}, supports, {thesis_atom}).",
        f"edge({premise_atom}, part_of, {arg_atom}).",
        "",
    ]
    return "\n".join(lines)


def serialize_scene(story_atom: str, scene_number: int, scene_title: str,
                    bridging_in: str, intention: str, conflict: str,
                    exposition: str, characterization: str, revelation: str,
                    outside_forces: str, bridging_out: str,
                    premise_atom: str = "",
                    beat_position: Optional[str] = None) -> str:
    """Serialize one scene as GAS scene slot + phase edges.

    Maps SceneMachine 8 nodes to GAS 7 canonical phases:
    - BridgingIn → bridging_in
    - IntentionInitialDirection → intention_initial_direction
    - Conflict → conflict
    - Exposition → exposition
    - Characterization → characterization
    - Revelation/OutsideForcesOrWin → climax (GAS combines these)
    - FollowUpBridgingOut → follow_up_bridging_out
    """
    scene_atom = f"scene_{scene_number}_{story_atom}"
    title_safe = _to_atom(scene_title) if scene_title else f"scene_{scene_number}"

    # Phase entity atoms
    bi = _to_atom(f"bi_{title_safe}")
    iid = _to_atom(f"iid_{title_safe}")
    conf = _to_atom(f"conf_{title_safe}")
    expo = _to_atom(f"expo_{title_safe}")
    char = _to_atom(f"char_{title_safe}")
    # GAS expects 'climax' — we map Revelation here (OutsideForcesOrWin is momentum)
    clim = _to_atom(f"clim_{title_safe}")
    fbo = _to_atom(f"fbo_{title_safe}")

    lines = [
        f"% === Scene {scene_number}: {scene_title} ===",
        f"slot({story_atom}, scene, {scene_atom}).",
        f"edge({scene_atom}, bridging_in, {bi}).",
        f"edge({scene_atom}, intention_initial_direction, {iid}).",
        f"edge({scene_atom}, conflict, {conf}).",
        f"edge({scene_atom}, exposition, {expo}).",
        f"edge({scene_atom}, characterization, {char}).",
        f"edge({scene_atom}, climax, {clim}).",
        f"edge({scene_atom}, follow_up_bridging_out, {fbo}).",
        "",
        f"% Phase content as kv",
        f"kv({bi}, text, {_quote_atom(bridging_in)}).",
        f"kv({iid}, text, {_quote_atom(intention)}).",
        f"kv({conf}, text, {_quote_atom(conflict)}).",
        f"kv({expo}, text, {_quote_atom(exposition)}).",
        f"kv({char}, text, {_quote_atom(characterization)}).",
        f"kv({clim}, text, {_quote_atom(revelation)}).",
        f"kv({fbo}, text, {_quote_atom(bridging_out)}).",
        "",
    ]

    # Premise links — phase entities test/advance the premise
    if premise_atom:
        lines.extend([
            f"% Premise instantiation",
            f"edge({conf}, tests, {premise_atom}).",
            f"edge({char}, advances, {premise_atom}).",
            f"edge({fbo}, advances, {premise_atom}).",
            "",
        ])

    # Beat position
    if beat_position:
        beat_atom = _to_atom(beat_position)
        lines.extend([
            f"edge({scene_atom}, maps_to_beat, {beat_atom}).",
            "",
        ])

    return "\n".join(lines)


def serialize_dialog(story_atom: str, scene_atom: str, dialog_index: int,
                     speaker: str, text: str, state: str = "glad") -> str:
    """Serialize one dialog line as GAS dialogue slot.

    Projects a CartON Dialog concept into GAS Prolog format.
    State must be one of: sad, glad, mad, scared (GAS canonical states).
    """
    line_atom = f"line_{dialog_index}_{scene_atom}"
    speaker_atom = _to_atom(speaker)

    lines = [
        f"slot({story_atom}, dialogue, {line_atom}).",
        f"kv({line_atom}, scene, {scene_atom}).",
        f"kv({line_atom}, speaker, {speaker_atom}).",
        f"kv({line_atom}, text, {_quote_atom(text)}).",
        f"kv({line_atom}, state, {state}).",
    ]
    return "\n".join(lines)


def serialize_scene_chain(story_atom: str, scene_count: int) -> str:
    """Serialize leads_to chain between scenes (required at depth 14+)."""
    lines = [f"% Scene chain (leads_to)"]
    for i in range(1, scene_count):
        prev = f"scene_{i}_{story_atom}"
        curr = f"scene_{i+1}_{story_atom}"
        lines.append(f"edge({prev}, leads_to, {curr}).")
    lines.append("")
    return "\n".join(lines)


def serialize_episode(episode_id: str, target_depth: int = 4,
                      twi_id: str = "", in_order_to: str = "",
                      learn_to_truly: str = "",
                      scenes: Optional[list] = None,
                      dialogs: Optional[list] = None) -> str:
    """Serialize a complete episode as GAS Prolog workspace.

    Args:
        episode_id: Episode identifier (becomes story atom)
        target_depth: GAS certification depth (4 = theme+scene, 20 = dialogue)
        twi_id: TWI concept name
        in_order_to: TWI in_order_to text
        learn_to_truly: TWI learn_to_truly text
        scenes: List of dicts with keys: scene_number, scene_title,
                bridging_in, intention, conflict, exposition,
                characterization, revelation, outside_forces, bridging_out,
                beat_position (optional)
        dialogs: List of dicts with keys: scene_number, speaker, text, state

    Returns:
        Complete Prolog workspace text ready for GAS evaluation.
    """
    story_atom = _to_atom(episode_id)
    scenes = scenes or []
    dialogs = dialogs or []

    # Determine premise atom from TWI
    premise_atom = f"premise_{_to_atom(twi_id)}" if twi_id else ""

    parts = [
        f"% GAS workspace for episode: {episode_id}",
        f"% Generated: {datetime.now().isoformat()}",
        f"% Target depth: {target_depth}",
        "",
        f"story({story_atom}).",
        f"target_depth({story_atom}, {target_depth}).",
        "",
    ]

    # Theme from TWI
    if twi_id and in_order_to and learn_to_truly:
        parts.append(serialize_twi(story_atom, twi_id, in_order_to, learn_to_truly))

    # Trope stub (required at depth 1+)
    if twi_id:
        trope_atom = f"trope_{story_atom}"
        parts.extend([
            f"% Trope (stub — agent should fill with specific trope)",
            f"slot({story_atom}, trope, {trope_atom}).",
            f"edge({trope_atom}, supports, {premise_atom}).",
            "",
        ])

    # Scenes
    for scene_data in scenes:
        parts.append(serialize_scene(
            story_atom=story_atom,
            scene_number=scene_data.get("scene_number", 1),
            scene_title=scene_data.get("scene_title", ""),
            bridging_in=scene_data.get("bridging_in", ""),
            intention=scene_data.get("intention", ""),
            conflict=scene_data.get("conflict", ""),
            exposition=scene_data.get("exposition", ""),
            characterization=scene_data.get("characterization", ""),
            revelation=scene_data.get("revelation", ""),
            outside_forces=scene_data.get("outside_forces", ""),
            bridging_out=scene_data.get("bridging_out", ""),
            premise_atom=premise_atom,
            beat_position=scene_data.get("beat_position"),
        ))

    # Scene chain
    if len(scenes) > 1:
        parts.append(serialize_scene_chain(story_atom, len(scenes)))

    # Dialogs
    if dialogs:
        parts.append("% === Dialogs ===")
        for i, dialog_data in enumerate(dialogs, 1):
            scene_num = dialog_data.get("scene_number", 1)
            scene_atom = f"scene_{scene_num}_{story_atom}"
            parts.append(serialize_dialog(
                story_atom=story_atom,
                scene_atom=scene_atom,
                dialog_index=i,
                speaker=dialog_data.get("speaker", "system"),
                text=dialog_data.get("text", ""),
                state=dialog_data.get("state", "glad"),
            ))
        parts.append("")

    return "\n".join(parts)
