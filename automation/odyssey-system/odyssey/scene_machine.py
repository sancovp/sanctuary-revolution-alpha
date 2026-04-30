"""
SceneMachine - Formal grammar for dramatic scene structure.

8-node scene flow encoding the craft of screenwriting into a machine-readable format.
Each node represents a dramatic beat; each beat contains typed screenplay paragraphs.

Origin: Isaac's Pydantic ontology (June 2025, herc agent session).
The LLM populates SceneMachine (creative beats). Deterministic assembler handles format.

Works alongside JourneyCore:
- JourneyCore = the JOURNEY arc (status_quo -> accomplishment + boon)
- SceneMachine = the SCENE engine (bridging_in -> bridging_out, per scene)

JourneyCore tells you WHAT the story is. SceneMachine tells you HOW each scene plays.
"""

from typing import Optional, List, Literal, Union
from pydantic import BaseModel, Field


# === ATOMIC SCREENPLAY ELEMENTS ===

class TextBlock(BaseModel):
    """Atomic text unit within a screenplay element."""
    text: str = Field(
        ...,
        description="The actual text content of this screenplay element."
    )
    style: Optional[str] = Field(
        default=None,
        description="Optional formatting style (e.g., 'Bold', 'Italic', 'Underline')."
    )


class SceneHeading(BaseModel):
    """INT./EXT. LOCATION - TIME OF DAY"""
    type: Literal["Scene Heading"] = "Scene Heading"
    text: TextBlock = Field(
        ...,
        description="Scene heading text. Format: INT./EXT. LOCATION - TIME"
    )


class Action(BaseModel):
    """Action/description lines in the screenplay."""
    type: Literal["Action"] = "Action"
    text: TextBlock = Field(
        ...,
        description="Action or description text. What we SEE and HEAR."
    )


class Character(BaseModel):
    """Character name cue before dialogue."""
    type: Literal["Character"] = "Character"
    text: TextBlock = Field(
        ...,
        description="Character name in CAPS."
    )


class Dialogue(BaseModel):
    """Spoken dialogue lines."""
    type: Literal["Dialogue"] = "Dialogue"
    text: TextBlock = Field(
        ...,
        description="The spoken dialogue text."
    )


class Parenthetical(BaseModel):
    """Acting direction within dialogue."""
    type: Literal["Parenthetical"] = "Parenthetical"
    text: TextBlock = Field(
        ...,
        description="Brief acting direction. (e.g., '(whispering)')"
    )


class Transition(BaseModel):
    """Scene transition directive."""
    type: Literal["Transition"] = "Transition"
    text: TextBlock = Field(
        ...,
        description="Transition text (e.g., 'CUT TO:', 'DISSOLVE TO:')"
    )


# Union of all paragraph element types
ParagraphElement = Union[SceneHeading, Action, Character, Dialogue, Parenthetical, Transition]


class Paragraph(BaseModel):
    """A typed screenplay paragraph — one or more elements in sequence."""
    type: Literal[
        "Scene Heading", "Action", "Character",
        "Dialogue", "Parenthetical", "Transition"
    ] = Field(
        ...,
        description="The primary type of this paragraph."
    )
    elements: List[TextBlock] = Field(
        ...,
        description="Text blocks composing this paragraph."
    )
    character: Optional[TextBlock] = Field(
        default=None,
        description="Character name if this paragraph is dialogue."
    )


# === THE 8-NODE SCENE FLOW ===

class BridgingIn(BaseModel):
    """Node 1: BRIDGING IN.

    Location and description. The protagonist or main scene character
    has shown up at the place they expect they will overcome the
    current obstacle for their current goal.
    """
    paragraphs: List[Paragraph] = Field(
        ...,
        description="Location + Description. Protagonist arrives at the place "
                    "they expect to overcome the current obstacle."
    )


class IntentionInitialDirection(BaseModel):
    """Node 2: INTENTION / INITIAL DIRECTION.

    First action line. Usually the character doing something related
    to trying to achieve the current goal.
    """
    paragraphs: List[Paragraph] = Field(
        ...,
        description="First action line. Character doing something "
                    "related to trying to achieve the current goal."
    )


class Conflict(BaseModel):
    """Node 3: CONFLICT.

    First action beat sequence. The protagonist or main scene character
    cannot immediately get what they want.
    """
    paragraphs: List[Paragraph] = Field(
        ...,
        description="First action beat. Protagonist cannot "
                    "immediately get what they want."
    )


class Exposition(BaseModel):
    """Node 4: EXPOSITION.

    Second action beat sequence. The underlying machinery of the conflict
    is explained or revealed to the protagonist or the scene's main character.
    """
    paragraphs: List[Paragraph] = Field(
        ...,
        description="Second action beat. The underlying machinery "
                    "of the conflict is explained or revealed."
    )


class Characterization(BaseModel):
    """Node 5: CHARACTERIZATION.

    Third action beat sequence. Characterizes the scene as it relates
    to the flaw of the protagonist or the main storyline if another
    character is central to this scene.
    """
    paragraphs: List[Paragraph] = Field(
        ...,
        description="Third action beat. Characterizes the scene as it "
                    "relates to the protagonist's flaw or main storyline."
    )


class Revelation(BaseModel):
    """Node 6: REVELATION.

    Until... revelation! A new discovery emerges that provides the
    correct direction for the character to go in.
    """
    paragraphs: List[Paragraph] = Field(
        ...,
        description="'Until... revelation!' A new discovery providing "
                    "the correct direction for the character."
    )


class OutsideForcesOrWin(BaseModel):
    """Node 7: OUTSIDE FORCES OR WIN.

    Outside force interferes OR A/B story win. This is often a sign
    of momentum — the character is moving in the right direction,
    so there is energetic flow happening.
    """
    paragraphs: List[Paragraph] = Field(
        ...,
        description="Outside force interferes OR A/B story win. "
                    "Sign of momentum and energetic flow."
    )


class FollowUpBridgingOut(BaseModel):
    """Node 8: FOLLOW UP & BRIDGING OUT.

    Action or dialogue lines connecting to the next bridging in
    section in the scene chain.
    """
    paragraphs: List[Paragraph] = Field(
        ...,
        description="Action or dialogue connecting to the next "
                    "scene's BridgingIn. The bridge out."
    )


# === THE MACHINE ===

class SceneMachine(BaseModel):
    """The scene engine. 8-node dramatic structure.

    Not just a data container — a codified grammar of storytelling.
    Each node is a dramatic beat that MUST be present for a scene
    to function as a complete narrative unit.

    Flow: BridgingIn -> Intention -> Conflict -> Exposition ->
          Characterization -> Revelation -> OutsideForcesOrWin ->
          FollowUpBridgingOut -> (next scene's BridgingIn)
    """
    scene_flow_node_1: BridgingIn = Field(
        ..., description="BRIDGING IN — location, setup, arrival"
    )
    scene_flow_node_2: IntentionInitialDirection = Field(
        ..., description="INTENTION — first action toward goal"
    )
    scene_flow_node_3: Conflict = Field(
        ..., description="CONFLICT — can't get what they want"
    )
    scene_flow_node_4: Exposition = Field(
        ..., description="EXPOSITION — conflict machinery revealed"
    )
    scene_flow_node_5: Characterization = Field(
        ..., description="CHARACTERIZATION — relates to protagonist flaw"
    )
    scene_flow_node_6: Revelation = Field(
        ..., description="REVELATION — new discovery, correct direction"
    )
    scene_flow_node_7: OutsideForcesOrWin = Field(
        ..., description="OUTSIDE FORCES / WIN — momentum, energetic flow"
    )
    scene_flow_node_8: FollowUpBridgingOut = Field(
        ..., description="BRIDGING OUT — connects to next scene"
    )


# === SCENE & CONTENT MODELS ===

class SceneModel(BaseModel):
    """A single scene: number + SceneMachine flow + beat position + dialogs."""
    scene_number: int = Field(
        ...,
        description="Position of this scene in the episode."
    )
    scene_title: Optional[str] = Field(
        default=None,
        description="Optional working title for this scene."
    )
    scene_machine: SceneMachine = Field(
        ...,
        description="The 8-node dramatic flow for this scene."
    )
    beat_position: Optional[str] = Field(
        default=None,
        description="HGS beat position (e.g. 'setup', 'fun_and_games', 'midpoint'). "
                    "Determines which act this scene belongs to. Stub — full model in GAS."
    )
    dialog_refs: List[str] = Field(
        default_factory=list,
        description="CartON concept refs for Dialog moments in this scene. "
                    "Dialogs live at the scene level — exact quotes from conversations."
    )
    proves_premise: Optional[str] = Field(
        default=None,
        description="Which grand argument premise this scene instantiates. "
                    "Scenes prove or disprove the theme — conflict and advancement are "
                    "dramatic elements orthogonal to theme proof. Stub — GAS validates this."
    )


class SceneMetadata(BaseModel):
    """Metadata about a screenplay or scene collection."""
    title: str = Field(..., description="Title of the screenplay.")
    author: str = Field(..., description="Author name.")
    genre: Optional[str] = Field(default=None, description="Genre.")
    logline: Optional[str] = Field(
        default=None,
        description="One-sentence summary of the story."
    )


# TODO: Screenplay model is WRONG. Scenes don't just go in a flat list.
# The full story hierarchy is ~400 nodes with multiple orders of higher
# constraints that scenes must satisfy. Isaac has the full hierarchy map.
# SceneMachine (the 8-node per-scene flow) is correct — Screenplay (the
# container/composition model) needs to be rebuilt from Isaac's hierarchy.
# DO NOT ship this model as-is for production use.
#
# class Screenplay(BaseModel):
#     metadata: SceneMetadata
#     scenes: List[SceneModel]  # WRONG — not a flat list
#     journey_core_name: Optional[str]
