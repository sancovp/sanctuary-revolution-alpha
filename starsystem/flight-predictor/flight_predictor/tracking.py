"""
Usage tracking for the Capability Predictor system.

This module handles:
- Recording actual tool/skill usage during sessions
- Storing observations to JSON files
- Computing mismatch statistics between predictions and actuals

Storage Location: /tmp/heaven_data/capability_tracker/

The tracking follows the CartON observation pattern:
predict → work (tracked) → compare → learn
"""

import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from .models import ActualUsage


# ============================================================================
# Configuration
# ============================================================================

# Default storage directory (can be overridden via CAPABILITY_TRACKER_DIR env var)
DEFAULT_STORAGE_DIR = Path(
    os.environ.get("CAPABILITY_TRACKER_DIR", "/tmp/heaven_data/capability_tracker")
)


def get_storage_dir() -> Path:
    """Get the storage directory, creating it if needed."""
    storage_dir = Path(
        os.environ.get("CAPABILITY_TRACKER_DIR", str(DEFAULT_STORAGE_DIR))
    )
    storage_dir.mkdir(parents=True, exist_ok=True)
    return storage_dir


def get_sessions_dir() -> Path:
    """Get the sessions directory."""
    sessions_dir = get_storage_dir() / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)
    return sessions_dir


def get_observations_dir() -> Path:
    """Get the observations directory."""
    obs_dir = get_storage_dir() / "observations"
    obs_dir.mkdir(parents=True, exist_ok=True)
    return obs_dir


# ============================================================================
# Session Management
# ============================================================================


class TrackingSession:
    """
    A tracking session that records tool/skill usage.

    A session is created when predictions are made, then updated
    as tools are actually used. Finally, it computes mismatches.
    """

    def __init__(
        self,
        session_id: Optional[str] = None,
        step_description: str = "",
        predicted_skills: Optional[list[str]] = None,
        predicted_tools: Optional[list[str]] = None,
    ):
        self.session_id = session_id or str(uuid.uuid4())[:8]
        self.step_description = step_description
        self.predicted_skills = predicted_skills or []
        self.predicted_tools = predicted_tools or []
        self.actual_skills: list[str] = []
        self.actual_tools: list[str] = []
        self.created_at = datetime.utcnow().isoformat()
        self.tool_events: list[dict] = []  # Raw event log

    def record_tool_use(self, tool_name: str, tool_input: Optional[dict] = None) -> None:
        """Record that a tool was used."""
        if tool_name not in self.actual_tools:
            self.actual_tools.append(tool_name)

        # Also log the event for debugging/analysis
        self.tool_events.append({
            "timestamp": datetime.utcnow().isoformat(),
            "tool_name": tool_name,
            "tool_input_keys": list(tool_input.keys()) if tool_input else [],
        })

    def record_skill_use(self, skill_name: str) -> None:
        """Record that a skill was used (equipped)."""
        if skill_name not in self.actual_skills:
            self.actual_skills.append(skill_name)

    def to_actual_usage(self) -> ActualUsage:
        """Convert to ActualUsage model for mismatch analysis."""
        return ActualUsage(
            session_id=self.session_id,
            step_description=self.step_description,
            predicted_skills=self.predicted_skills,
            predicted_tools=self.predicted_tools,
            actual_skills=self.actual_skills,
            actual_tools=self.actual_tools,
        )

    def to_dict(self) -> dict:
        """Serialize to dictionary for JSON storage."""
        return {
            "session_id": self.session_id,
            "step_description": self.step_description,
            "predicted_skills": self.predicted_skills,
            "predicted_tools": self.predicted_tools,
            "actual_skills": self.actual_skills,
            "actual_tools": self.actual_tools,
            "created_at": self.created_at,
            "tool_events": self.tool_events,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TrackingSession":
        """Deserialize from dictionary."""
        session = cls(
            session_id=data["session_id"],
            step_description=data.get("step_description", ""),
            predicted_skills=data.get("predicted_skills", []),
            predicted_tools=data.get("predicted_tools", []),
        )
        session.actual_skills = data.get("actual_skills", [])
        session.actual_tools = data.get("actual_tools", [])
        session.created_at = data.get("created_at", datetime.utcnow().isoformat())
        session.tool_events = data.get("tool_events", [])
        return session


# ============================================================================
# Storage Functions
# ============================================================================


def save_session(session: TrackingSession) -> Path:
    """Save a tracking session to disk."""
    sessions_dir = get_sessions_dir()
    filename = f"{session.session_id}.json"
    filepath = sessions_dir / filename

    filepath.write_text(json.dumps(session.to_dict(), indent=2))
    return filepath


def load_session(session_id: str) -> Optional[TrackingSession]:
    """Load a tracking session from disk."""
    sessions_dir = get_sessions_dir()
    filepath = sessions_dir / f"{session_id}.json"

    if not filepath.exists():
        return None

    data = json.loads(filepath.read_text())
    return TrackingSession.from_dict(data)


def get_active_session() -> Optional[TrackingSession]:
    """
    Get the currently active session.

    The active session is stored in a special file that points to
    the current session ID. This allows the hook to know which
    session to update.
    """
    active_file = get_storage_dir() / "active_session.json"

    if not active_file.exists():
        return None

    try:
        data = json.loads(active_file.read_text())
        session_id = data.get("session_id")
        if session_id:
            return load_session(session_id)
    except Exception:
        pass

    return None


def set_active_session(session: TrackingSession) -> None:
    """Set the currently active session."""
    active_file = get_storage_dir() / "active_session.json"
    active_file.write_text(json.dumps({
        "session_id": session.session_id,
        "started_at": datetime.utcnow().isoformat(),
    }, indent=2))

    # Also save the session itself
    save_session(session)


def clear_active_session() -> None:
    """Clear the active session marker."""
    active_file = get_storage_dir() / "active_session.json"
    if active_file.exists():
        active_file.unlink()


# ============================================================================
# Observation Storage
# ============================================================================


def save_observation(usage: ActualUsage) -> Path:
    """
    Save an observation (completed session with mismatch data).

    Observations are stored separately from sessions because they
    represent completed data that can be aggregated for learning.
    """
    obs_dir = get_observations_dir()
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{usage.session_id}.json"
    filepath = obs_dir / filename

    # Include mismatch analysis in the saved data
    data = {
        "session_id": usage.session_id,
        "step_description": usage.step_description,
        "predicted_skills": usage.predicted_skills,
        "predicted_tools": usage.predicted_tools,
        "actual_skills": usage.actual_skills,
        "actual_tools": usage.actual_tools,
        "analysis": {
            "skill_true_positives": usage.skill_true_positives,
            "skill_false_positives": usage.skill_false_positives,
            "skill_false_negatives": usage.skill_false_negatives,
            "tool_true_positives": usage.tool_true_positives,
            "tool_false_positives": usage.tool_false_positives,
            "tool_false_negatives": usage.tool_false_negatives,
        },
        "saved_at": datetime.utcnow().isoformat(),
    }

    filepath.write_text(json.dumps(data, indent=2))
    return filepath


def load_all_observations() -> list[dict]:
    """Load all observations for aggregation."""
    obs_dir = get_observations_dir()
    observations = []

    for filepath in sorted(obs_dir.glob("*.json")):
        try:
            data = json.loads(filepath.read_text())
            observations.append(data)
        except Exception:
            continue

    return observations


# ============================================================================
# Hook Integration
# ============================================================================


def record_tool_from_hook(tool_name: str, tool_input: Optional[dict] = None) -> bool:
    """
    Record a tool use from a PostToolUse hook.

    This is the main entry point for the hook to record usage.
    Returns True if recorded successfully, False if no active session.
    """
    session = get_active_session()
    if session is None:
        return False

    session.record_tool_use(tool_name, tool_input)
    save_session(session)
    return True


def start_tracking_session(
    step_description: str = "",
    predicted_skills: Optional[list[str]] = None,
    predicted_tools: Optional[list[str]] = None,
    session_id: Optional[str] = None,
) -> TrackingSession:
    """
    Start a new tracking session.

    Call this after making predictions but before executing work.
    """
    session = TrackingSession(
        session_id=session_id,
        step_description=step_description,
        predicted_skills=predicted_skills,
        predicted_tools=predicted_tools,
    )
    set_active_session(session)
    return session


def end_tracking_session() -> Optional[ActualUsage]:
    """
    End the current tracking session and save observation.

    Returns the ActualUsage with mismatch data, or None if no active session.
    """
    session = get_active_session()
    if session is None:
        return None

    usage = session.to_actual_usage()
    save_observation(usage)
    clear_active_session()

    return usage


# ============================================================================
# Mismatch Reporting
# ============================================================================


def format_mismatch_report(usage: ActualUsage) -> str:
    """Format a human-readable mismatch report."""
    lines = [
        f"=== Capability Tracking Report ===",
        f"Session: {usage.session_id}",
        f"Step: {usage.step_description or '(no description)'}",
        "",
        "--- Skills ---",
        f"Predicted: {', '.join(usage.predicted_skills) or '(none)'}",
        f"Actual: {', '.join(usage.actual_skills) or '(none)'}",
        f"✓ True Positives: {', '.join(usage.skill_true_positives) or '(none)'}",
        f"✗ False Positives (predicted, not used): {', '.join(usage.skill_false_positives) or '(none)'}",
        f"✗ False Negatives (used, not predicted): {', '.join(usage.skill_false_negatives) or '(none)'}",
        "",
        "--- Tools ---",
        f"Predicted: {', '.join(usage.predicted_tools) or '(none)'}",
        f"Actual: {', '.join(usage.actual_tools) or '(none)'}",
        f"✓ True Positives: {', '.join(usage.tool_true_positives) or '(none)'}",
        f"✗ False Positives (predicted, not used): {', '.join(usage.tool_false_positives) or '(none)'}",
        f"✗ False Negatives (used, not predicted): {', '.join(usage.tool_false_negatives) or '(none)'}",
    ]
    return "\n".join(lines)


# ============================================================================
# Rollup Aggregation (Phase 3.3)
# ============================================================================


def extract_keywords(text: str) -> list[str]:
    """
    Extract meaningful keywords from step descriptions.

    Simple tokenization + filtering for common English stop words.
    """
    import re

    # Common stop words to filter out
    STOP_WORDS = {
        "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "by", "from", "as", "is", "was", "are", "were", "been",
        "be", "have", "has", "had", "do", "does", "did", "will", "would",
        "could", "should", "may", "might", "must", "shall", "can", "need",
        "this", "that", "these", "those", "it", "its", "i", "we", "you",
        "he", "she", "they", "me", "us", "him", "her", "them", "my", "our",
        "your", "his", "their", "what", "which", "who", "whom", "when",
        "where", "why", "how", "all", "each", "every", "both", "few",
        "more", "most", "other", "some", "such", "no", "not", "only",
        "same", "so", "than", "too", "very", "just", "also", "now", "then",
    }

    # Tokenize: split on non-alphanumeric, lowercase
    tokens = re.findall(r'[a-zA-Z0-9]+', text.lower())

    # Filter: remove stop words and very short tokens
    keywords = [t for t in tokens if t not in STOP_WORDS and len(t) > 2]

    return keywords


class CapabilityRollup:
    """
    Aggregates observations to find keyword → capability patterns.

    Patterns like:
        "plan" → [starlog: 95%, waypoint: 80%, flight-config: 60%]
        "code" → [Write: 90%, Edit: 85%, context-alignment: 70%]

    These are used to improve prediction accuracy over time.
    """

    def __init__(self):
        # keyword → {capability_name: count}
        self.skill_counts: dict[str, dict[str, int]] = {}
        self.tool_counts: dict[str, dict[str, int]] = {}

        # keyword → total observations containing that keyword
        self.keyword_observations: dict[str, int] = {}

        # Overall counts for computing priors
        self.total_observations: int = 0
        self.skill_totals: dict[str, int] = {}
        self.tool_totals: dict[str, int] = {}

    def add_observation(self, observation: dict) -> None:
        """
        Add a single observation to the rollup.

        Args:
            observation: Dict from load_all_observations() with keys:
                - step_description
                - actual_skills
                - actual_tools
        """
        step_desc = observation.get("step_description", "")
        actual_skills = observation.get("actual_skills", [])
        actual_tools = observation.get("actual_tools", [])

        # Extract keywords from the step description
        keywords = extract_keywords(step_desc)

        if not keywords:
            return

        self.total_observations += 1

        # Update keyword observation counts
        unique_keywords = set(keywords)
        for kw in unique_keywords:
            self.keyword_observations[kw] = self.keyword_observations.get(kw, 0) + 1

        # Update skill counts per keyword
        for kw in unique_keywords:
            if kw not in self.skill_counts:
                self.skill_counts[kw] = {}
            for skill in actual_skills:
                self.skill_counts[kw][skill] = self.skill_counts[kw].get(skill, 0) + 1

        # Update tool counts per keyword
        for kw in unique_keywords:
            if kw not in self.tool_counts:
                self.tool_counts[kw] = {}
            for tool in actual_tools:
                self.tool_counts[kw][tool] = self.tool_counts[kw].get(tool, 0) + 1

        # Update overall totals
        for skill in actual_skills:
            self.skill_totals[skill] = self.skill_totals.get(skill, 0) + 1
        for tool in actual_tools:
            self.tool_totals[tool] = self.tool_totals.get(tool, 0) + 1

    def get_skill_probabilities(self, keyword: str) -> list[tuple[str, float]]:
        """
        Get skill probabilities for a keyword.

        Returns list of (skill_name, probability) sorted by probability descending.
        Probability = count(keyword AND skill) / count(keyword)
        """
        if keyword not in self.skill_counts:
            return []

        kw_count = self.keyword_observations.get(keyword, 1)
        probs = []

        for skill, count in self.skill_counts[keyword].items():
            prob = count / kw_count
            probs.append((skill, prob))

        return sorted(probs, key=lambda x: x[1], reverse=True)

    def get_tool_probabilities(self, keyword: str) -> list[tuple[str, float]]:
        """
        Get tool probabilities for a keyword.

        Returns list of (tool_name, probability) sorted by probability descending.
        Probability = count(keyword AND tool) / count(keyword)
        """
        if keyword not in self.tool_counts:
            return []

        kw_count = self.keyword_observations.get(keyword, 1)
        probs = []

        for tool, count in self.tool_counts[keyword].items():
            prob = count / kw_count
            probs.append((tool, prob))

        return sorted(probs, key=lambda x: x[1], reverse=True)

    def get_aggregated_predictions(
        self, query: str, top_k: int = 5
    ) -> dict[str, list[tuple[str, float]]]:
        """
        Get aggregated predictions for a query string.

        Extracts keywords from query, looks up probabilities for each,
        and combines them into weighted predictions.

        Args:
            query: Natural language query/description
            top_k: Number of top predictions to return

        Returns:
            Dict with 'skills' and 'tools' keys, each containing
            list of (name, score) tuples sorted by score descending.
        """
        keywords = extract_keywords(query)

        # Aggregate skill scores across all keywords
        skill_scores: dict[str, float] = {}
        for kw in keywords:
            for skill, prob in self.get_skill_probabilities(kw):
                # Simple additive scoring
                skill_scores[skill] = skill_scores.get(skill, 0.0) + prob

        # Aggregate tool scores across all keywords
        tool_scores: dict[str, float] = {}
        for kw in keywords:
            for tool, prob in self.get_tool_probabilities(kw):
                tool_scores[tool] = tool_scores.get(tool, 0.0) + prob

        # Normalize by number of keywords
        if keywords:
            for skill in skill_scores:
                skill_scores[skill] /= len(keywords)
            for tool in tool_scores:
                tool_scores[tool] /= len(keywords)

        # Sort and take top k
        top_skills = sorted(skill_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
        top_tools = sorted(tool_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

        return {
            "skills": top_skills,
            "tools": top_tools,
        }

    def to_dict(self) -> dict:
        """Serialize to dictionary for storage."""
        return {
            "skill_counts": self.skill_counts,
            "tool_counts": self.tool_counts,
            "keyword_observations": self.keyword_observations,
            "total_observations": self.total_observations,
            "skill_totals": self.skill_totals,
            "tool_totals": self.tool_totals,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CapabilityRollup":
        """Deserialize from dictionary."""
        rollup = cls()
        rollup.skill_counts = data.get("skill_counts", {})
        rollup.tool_counts = data.get("tool_counts", {})
        rollup.keyword_observations = data.get("keyword_observations", {})
        rollup.total_observations = data.get("total_observations", 0)
        rollup.skill_totals = data.get("skill_totals", {})
        rollup.tool_totals = data.get("tool_totals", {})
        return rollup


def get_rollup_file() -> Path:
    """Get the rollup aggregation file path."""
    return get_storage_dir() / "rollup.json"


def save_rollup(rollup: CapabilityRollup) -> Path:
    """Save rollup aggregation to disk."""
    filepath = get_rollup_file()
    filepath.write_text(json.dumps(rollup.to_dict(), indent=2))
    return filepath


def load_rollup() -> Optional[CapabilityRollup]:
    """Load rollup aggregation from disk."""
    filepath = get_rollup_file()
    if not filepath.exists():
        return None

    try:
        data = json.loads(filepath.read_text())
        return CapabilityRollup.from_dict(data)
    except Exception:
        return None


def compute_rollup() -> CapabilityRollup:
    """
    Compute rollup aggregation from all stored observations.

    This re-computes the entire rollup from scratch. Use this
    to rebuild after observations accumulate.

    Returns:
        CapabilityRollup with aggregated keyword → capability mappings
    """
    rollup = CapabilityRollup()

    for observation in load_all_observations():
        rollup.add_observation(observation)

    # Save the computed rollup
    save_rollup(rollup)

    return rollup


# ============================================================================
# Mismatch Detection and Reporting (Phase 3.4)
# ============================================================================


class MismatchAnalysis:
    """
    Aggregated mismatch analysis across all observations.

    Computes precision, recall, F1 scores for both skills and tools,
    and identifies patterns in prediction failures.
    """

    def __init__(self):
        # Counters for skill predictions
        self.skill_true_positives: int = 0
        self.skill_false_positives: int = 0
        self.skill_false_negatives: int = 0

        # Counters for tool predictions
        self.tool_true_positives: int = 0
        self.tool_false_positives: int = 0
        self.tool_false_negatives: int = 0

        # Track frequency of misses (things we failed to predict)
        self.skill_misses: dict[str, int] = {}  # skill_name -> count
        self.tool_misses: dict[str, int] = {}  # tool_name -> count

        # Track frequency of over-predictions (things we predicted but weren't used)
        self.skill_over_predictions: dict[str, int] = {}
        self.tool_over_predictions: dict[str, int] = {}

        # Track frequency of correct predictions (things we got right)
        self.skill_hits: dict[str, int] = {}
        self.tool_hits: dict[str, int] = {}

        # Total observations analyzed
        self.total_observations: int = 0

    @property
    def skill_precision(self) -> float:
        """Precision = TP / (TP + FP) - how often our predictions are correct."""
        total_predicted = self.skill_true_positives + self.skill_false_positives
        if total_predicted == 0:
            return 0.0
        return self.skill_true_positives / total_predicted

    @property
    def skill_recall(self) -> float:
        """Recall = TP / (TP + FN) - how often we predict things that are used."""
        total_actual = self.skill_true_positives + self.skill_false_negatives
        if total_actual == 0:
            return 0.0
        return self.skill_true_positives / total_actual

    @property
    def skill_f1(self) -> float:
        """F1 = 2 * (precision * recall) / (precision + recall)."""
        p, r = self.skill_precision, self.skill_recall
        if p + r == 0:
            return 0.0
        return 2 * (p * r) / (p + r)

    @property
    def tool_precision(self) -> float:
        """Precision = TP / (TP + FP) - how often our predictions are correct."""
        total_predicted = self.tool_true_positives + self.tool_false_positives
        if total_predicted == 0:
            return 0.0
        return self.tool_true_positives / total_predicted

    @property
    def tool_recall(self) -> float:
        """Recall = TP / (TP + FN) - how often we predict things that are used."""
        total_actual = self.tool_true_positives + self.tool_false_negatives
        if total_actual == 0:
            return 0.0
        return self.tool_true_positives / total_actual

    @property
    def tool_f1(self) -> float:
        """F1 = 2 * (precision * recall) / (precision + recall)."""
        p, r = self.tool_precision, self.tool_recall
        if p + r == 0:
            return 0.0
        return 2 * (p * r) / (p + r)

    def add_observation(self, observation: dict) -> None:
        """
        Add an observation's mismatch data to the analysis.

        Args:
            observation: Dict from load_all_observations() with 'analysis' key
        """
        self.total_observations += 1

        analysis = observation.get("analysis", {})

        # Count skill metrics
        skill_tp = analysis.get("skill_true_positives", [])
        skill_fp = analysis.get("skill_false_positives", [])
        skill_fn = analysis.get("skill_false_negatives", [])

        self.skill_true_positives += len(skill_tp)
        self.skill_false_positives += len(skill_fp)
        self.skill_false_negatives += len(skill_fn)

        # Track individual skill patterns
        for skill in skill_tp:
            self.skill_hits[skill] = self.skill_hits.get(skill, 0) + 1
        for skill in skill_fp:
            self.skill_over_predictions[skill] = self.skill_over_predictions.get(skill, 0) + 1
        for skill in skill_fn:
            self.skill_misses[skill] = self.skill_misses.get(skill, 0) + 1

        # Count tool metrics
        tool_tp = analysis.get("tool_true_positives", [])
        tool_fp = analysis.get("tool_false_positives", [])
        tool_fn = analysis.get("tool_false_negatives", [])

        self.tool_true_positives += len(tool_tp)
        self.tool_false_positives += len(tool_fp)
        self.tool_false_negatives += len(tool_fn)

        # Track individual tool patterns
        for tool in tool_tp:
            self.tool_hits[tool] = self.tool_hits.get(tool, 0) + 1
        for tool in tool_fp:
            self.tool_over_predictions[tool] = self.tool_over_predictions.get(tool, 0) + 1
        for tool in tool_fn:
            self.tool_misses[tool] = self.tool_misses.get(tool, 0) + 1

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "total_observations": self.total_observations,
            "skills": {
                "true_positives": self.skill_true_positives,
                "false_positives": self.skill_false_positives,
                "false_negatives": self.skill_false_negatives,
                "precision": self.skill_precision,
                "recall": self.skill_recall,
                "f1": self.skill_f1,
                "top_misses": sorted(
                    self.skill_misses.items(), key=lambda x: x[1], reverse=True
                )[:10],
                "top_over_predictions": sorted(
                    self.skill_over_predictions.items(), key=lambda x: x[1], reverse=True
                )[:10],
                "top_hits": sorted(
                    self.skill_hits.items(), key=lambda x: x[1], reverse=True
                )[:10],
            },
            "tools": {
                "true_positives": self.tool_true_positives,
                "false_positives": self.tool_false_positives,
                "false_negatives": self.tool_false_negatives,
                "precision": self.tool_precision,
                "recall": self.tool_recall,
                "f1": self.tool_f1,
                "top_misses": sorted(
                    self.tool_misses.items(), key=lambda x: x[1], reverse=True
                )[:10],
                "top_over_predictions": sorted(
                    self.tool_over_predictions.items(), key=lambda x: x[1], reverse=True
                )[:10],
                "top_hits": sorted(
                    self.tool_hits.items(), key=lambda x: x[1], reverse=True
                )[:10],
            },
        }


def compute_mismatch_analysis() -> MismatchAnalysis:
    """
    Compute mismatch analysis from all stored observations.

    Returns:
        MismatchAnalysis with precision/recall/F1 and failure patterns
    """
    analysis = MismatchAnalysis()

    for observation in load_all_observations():
        analysis.add_observation(observation)

    return analysis


def get_improvement_suggestions(analysis: MismatchAnalysis, top_n: int = 5) -> list[str]:
    """
    Generate actionable improvement suggestions based on mismatch analysis.

    Args:
        analysis: The computed mismatch analysis
        top_n: Number of top items to include in suggestions

    Returns:
        List of suggestion strings
    """
    suggestions = []

    # If no data yet
    if analysis.total_observations == 0:
        return ["No observations recorded yet. Run some predictions and track actual usage to get suggestions."]

    # Skill-related suggestions
    if analysis.skill_false_negatives > 0:
        top_misses = sorted(
            analysis.skill_misses.items(), key=lambda x: x[1], reverse=True
        )[:top_n]
        if top_misses:
            missed_list = ", ".join(f"'{s}' ({c}x)" for s, c in top_misses)
            suggestions.append(
                f"SKILL MISSES (used but not predicted): {missed_list}. "
                "Consider adding keyword associations for these skills in the rollup."
            )

    if analysis.skill_false_positives > 0:
        top_over = sorted(
            analysis.skill_over_predictions.items(), key=lambda x: x[1], reverse=True
        )[:top_n]
        if top_over:
            over_list = ", ".join(f"'{s}' ({c}x)" for s, c in top_over)
            suggestions.append(
                f"SKILL OVER-PREDICTIONS (predicted but not used): {over_list}. "
                "Consider reducing the confidence weight for these skills."
            )

    # Tool-related suggestions
    if analysis.tool_false_negatives > 0:
        top_misses = sorted(
            analysis.tool_misses.items(), key=lambda x: x[1], reverse=True
        )[:top_n]
        if top_misses:
            missed_list = ", ".join(f"'{t}' ({c}x)" for t, c in top_misses)
            suggestions.append(
                f"TOOL MISSES (used but not predicted): {missed_list}. "
                "Consider adding keyword associations for these tools in the rollup."
            )

    if analysis.tool_false_positives > 0:
        top_over = sorted(
            analysis.tool_over_predictions.items(), key=lambda x: x[1], reverse=True
        )[:top_n]
        if top_over:
            over_list = ", ".join(f"'{t}' ({c}x)" for t, c in top_over)
            suggestions.append(
                f"TOOL OVER-PREDICTIONS (predicted but not used): {over_list}. "
                "Consider reducing the confidence weight for these tools."
            )

    # Overall suggestions based on metrics
    if analysis.skill_precision < 0.5 and analysis.skill_true_positives > 0:
        suggestions.append(
            f"Skill precision is low ({analysis.skill_precision:.0%}). "
            "Predictions are too broad - consider adding more specific keyword mappings."
        )

    if analysis.skill_recall < 0.5 and analysis.skill_true_positives > 0:
        suggestions.append(
            f"Skill recall is low ({analysis.skill_recall:.0%}). "
            "Many skills are missed - consider expanding the skill catalog coverage."
        )

    if analysis.tool_precision < 0.5 and analysis.tool_true_positives > 0:
        suggestions.append(
            f"Tool precision is low ({analysis.tool_precision:.0%}). "
            "Predictions are too broad - consider adding more specific keyword mappings."
        )

    if analysis.tool_recall < 0.5 and analysis.tool_true_positives > 0:
        suggestions.append(
            f"Tool recall is low ({analysis.tool_recall:.0%}). "
            "Many tools are missed - consider expanding the tool catalog coverage."
        )

    if not suggestions:
        suggestions.append(
            f"Prediction quality is good! "
            f"Skill F1: {analysis.skill_f1:.0%}, Tool F1: {analysis.tool_f1:.0%}"
        )

    return suggestions


def format_mismatch_analysis_report(analysis: MismatchAnalysis) -> str:
    """
    Format a comprehensive human-readable mismatch analysis report.

    Args:
        analysis: The computed mismatch analysis

    Returns:
        Formatted report string
    """
    lines = [
        "=" * 60,
        "CAPABILITY PREDICTION MISMATCH ANALYSIS",
        "=" * 60,
        f"Total Observations Analyzed: {analysis.total_observations}",
        "",
    ]

    if analysis.total_observations == 0:
        lines.append("No observations recorded yet.")
        return "\n".join(lines)

    # Skill metrics
    lines.extend([
        "--- SKILL PREDICTIONS ---",
        f"True Positives:  {analysis.skill_true_positives:4d}  (predicted AND used)",
        f"False Positives: {analysis.skill_false_positives:4d}  (predicted but NOT used)",
        f"False Negatives: {analysis.skill_false_negatives:4d}  (used but NOT predicted)",
        "",
        f"Precision: {analysis.skill_precision:6.1%}  (of predictions, how many were correct)",
        f"Recall:    {analysis.skill_recall:6.1%}  (of actual usage, how many were predicted)",
        f"F1 Score:  {analysis.skill_f1:6.1%}  (harmonic mean of precision & recall)",
        "",
    ])

    # Top skill misses
    if analysis.skill_misses:
        lines.append("Top Skill Misses (LEARN these mappings):")
        for skill, count in sorted(
            analysis.skill_misses.items(), key=lambda x: x[1], reverse=True
        )[:5]:
            lines.append(f"  → {skill}: {count}x")
        lines.append("")

    # Top skill over-predictions
    if analysis.skill_over_predictions:
        lines.append("Top Skill Over-Predictions (REDUCE these weights):")
        for skill, count in sorted(
            analysis.skill_over_predictions.items(), key=lambda x: x[1], reverse=True
        )[:5]:
            lines.append(f"  → {skill}: {count}x")
        lines.append("")

    # Tool metrics
    lines.extend([
        "--- TOOL PREDICTIONS ---",
        f"True Positives:  {analysis.tool_true_positives:4d}  (predicted AND used)",
        f"False Positives: {analysis.tool_false_positives:4d}  (predicted but NOT used)",
        f"False Negatives: {analysis.tool_false_negatives:4d}  (used but NOT predicted)",
        "",
        f"Precision: {analysis.tool_precision:6.1%}  (of predictions, how many were correct)",
        f"Recall:    {analysis.tool_recall:6.1%}  (of actual usage, how many were predicted)",
        f"F1 Score:  {analysis.tool_f1:6.1%}  (harmonic mean of precision & recall)",
        "",
    ])

    # Top tool misses
    if analysis.tool_misses:
        lines.append("Top Tool Misses (LEARN these mappings):")
        for tool, count in sorted(
            analysis.tool_misses.items(), key=lambda x: x[1], reverse=True
        )[:5]:
            lines.append(f"  → {tool}: {count}x")
        lines.append("")

    # Top tool over-predictions
    if analysis.tool_over_predictions:
        lines.append("Top Tool Over-Predictions (REDUCE these weights):")
        for tool, count in sorted(
            analysis.tool_over_predictions.items(), key=lambda x: x[1], reverse=True
        )[:5]:
            lines.append(f"  → {tool}: {count}x")
        lines.append("")

    # Improvement suggestions
    suggestions = get_improvement_suggestions(analysis)
    lines.extend([
        "--- IMPROVEMENT SUGGESTIONS ---",
    ])
    for i, suggestion in enumerate(suggestions, 1):
        lines.append(f"{i}. {suggestion}")

    lines.append("=" * 60)
    return "\n".join(lines)


# ============================================================================
# Feedback Loop Integration (Phase 4.1)
# ============================================================================


class FeedbackLoop:
    """
    Manages the complete feedback loop for capability prediction tuning.

    The loop:
    1. predict_capabilities() generates initial predictions
    2. get_augmented_predictions() enhances with rollup-learned patterns
    3. Work happens (tools used, tracked via hooks)
    4. end_tracking_session() saves observation
    5. update_from_session() incorporates new data into rollup
    6. Next prediction is better because rollup has more data

    Usage:
        >>> loop = FeedbackLoop()
        >>> # Before work: get augmented predictions
        >>> augmented = loop.get_augmented_predictions("implement the feature")
        >>> # Start tracking
        >>> loop.start_session("implement the feature", augmented["skills"], augmented["tools"])
        >>> # Work happens...
        >>> # End session and update loop
        >>> loop.end_session_and_update()
    """

    def __init__(self):
        self._rollup: Optional[CapabilityRollup] = None

    @property
    def rollup(self) -> CapabilityRollup:
        """Get or load the rollup (lazy loading)."""
        if self._rollup is None:
            loaded = load_rollup()
            self._rollup = loaded if loaded else CapabilityRollup()
        return self._rollup

    def get_augmented_predictions(
        self,
        query: str,
        rag_skills: Optional[list[str]] = None,
        rag_tools: Optional[list[str]] = None,
        rag_weight: float = 0.5,
        rollup_weight: float = 0.3,
        alias_weight: float = 0.2,
        top_k: int = 5,
        use_alias_clusters: bool = True,
    ) -> dict[str, list[tuple[str, float]]]:
        """
        Get augmented predictions by combining RAG, rollup, and alias clusters.

        The feedback loop effect: rollup has learned from past observations
        which capabilities were ACTUALLY used for similar queries. Alias clusters
        provide bootstrap predictions when observation data is sparse.

        Args:
            query: Natural language description (e.g., step description)
            rag_skills: Skills predicted by RAG (from predict_capabilities)
            rag_tools: Tools predicted by RAG (from predict_capabilities)
            rag_weight: Weight for RAG predictions (default 0.5)
            rollup_weight: Weight for rollup predictions (default 0.3)
            alias_weight: Weight for alias cluster predictions (default 0.2)
            top_k: Number of top predictions to return
            use_alias_clusters: Whether to use alias cluster bootstrapping (default True)

        Returns:
            Dict with 'skills' and 'tools' keys, each containing
            list of (name, combined_score) tuples sorted by score descending.
        """
        # Get rollup-based predictions
        rollup_preds = self.rollup.get_aggregated_predictions(query, top_k=top_k * 2)

        # Combine with RAG predictions
        skill_scores: dict[str, float] = {}
        tool_scores: dict[str, float] = {}

        # Add RAG predictions with weight
        if rag_skills:
            for i, skill in enumerate(rag_skills):
                # Higher rank = higher score (1.0 for first, decreasing)
                base_score = 1.0 - (i * 0.1)
                skill_scores[skill] = skill_scores.get(skill, 0.0) + (base_score * rag_weight)

        if rag_tools:
            for i, tool in enumerate(rag_tools):
                base_score = 1.0 - (i * 0.1)
                tool_scores[tool] = tool_scores.get(tool, 0.0) + (base_score * rag_weight)

        # Add rollup predictions with weight
        for skill, prob in rollup_preds.get("skills", []):
            skill_scores[skill] = skill_scores.get(skill, 0.0) + (prob * rollup_weight)

        for tool, prob in rollup_preds.get("tools", []):
            tool_scores[tool] = tool_scores.get(tool, 0.0) + (prob * rollup_weight)

        # Add alias cluster predictions with weight (Phase 4.2)
        if use_alias_clusters:
            from .alias_clusters import get_bootstrap_predictions
            alias_preds = get_bootstrap_predictions(query, top_k=top_k * 2)

            for skill, score in alias_preds.get("skills", []):
                skill_scores[skill] = skill_scores.get(skill, 0.0) + (score * alias_weight)

            for tool, score in alias_preds.get("tools", []):
                tool_scores[tool] = tool_scores.get(tool, 0.0) + (score * alias_weight)

        # Sort and take top k
        top_skills = sorted(skill_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
        top_tools = sorted(tool_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

        return {
            "skills": top_skills,
            "tools": top_tools,
        }

    def start_session(
        self,
        step_description: str,
        predicted_skills: Optional[list[str]] = None,
        predicted_tools: Optional[list[str]] = None,
        session_id: Optional[str] = None,
    ) -> TrackingSession:
        """
        Start a tracking session for the feedback loop.

        Call this after getting predictions but before executing work.
        """
        return start_tracking_session(
            step_description=step_description,
            predicted_skills=predicted_skills,
            predicted_tools=predicted_tools,
            session_id=session_id,
        )

    def end_session_and_update(self) -> Optional[dict]:
        """
        End the current session and update the rollup with new observation.

        This is where the feedback loop closes:
        1. End session saves observation with mismatch data
        2. Observation is added to rollup
        3. Rollup is saved for next prediction

        Returns:
            Dict with 'usage' (ActualUsage data) and 'rollup_updated' (bool)
            or None if no active session.
        """
        usage = end_tracking_session()
        if usage is None:
            return None

        # Add this observation to the rollup
        observation = {
            "step_description": usage.step_description,
            "actual_skills": usage.actual_skills,
            "actual_tools": usage.actual_tools,
        }
        self.rollup.add_observation(observation)

        # Save updated rollup
        save_rollup(self.rollup)

        return {
            "usage": {
                "session_id": usage.session_id,
                "step_description": usage.step_description,
                "skill_true_positives": usage.skill_true_positives,
                "skill_false_positives": usage.skill_false_positives,
                "skill_false_negatives": usage.skill_false_negatives,
                "tool_true_positives": usage.tool_true_positives,
                "tool_false_positives": usage.tool_false_positives,
                "tool_false_negatives": usage.tool_false_negatives,
            },
            "rollup_updated": True,
            "rollup_total_observations": self.rollup.total_observations,
        }

    def get_feedback_stats(self) -> dict:
        """
        Get statistics about the feedback loop performance.

        Returns metrics about how well predictions match actual usage
        based on all stored observations.
        """
        analysis = compute_mismatch_analysis()
        suggestions = get_improvement_suggestions(analysis)

        return {
            "total_observations": analysis.total_observations,
            "skill_precision": analysis.skill_precision,
            "skill_recall": analysis.skill_recall,
            "skill_f1": analysis.skill_f1,
            "tool_precision": analysis.tool_precision,
            "tool_recall": analysis.tool_recall,
            "tool_f1": analysis.tool_f1,
            "rollup_keywords": len(self.rollup.keyword_observations),
            "suggestions": suggestions,
        }

    def reset_rollup(self) -> None:
        """Reset the rollup to empty state (for testing or fresh start)."""
        self._rollup = CapabilityRollup()
        save_rollup(self._rollup)


# Global feedback loop instance for convenience
_feedback_loop: Optional[FeedbackLoop] = None


def get_feedback_loop() -> FeedbackLoop:
    """Get the global FeedbackLoop instance (creates if needed)."""
    global _feedback_loop
    if _feedback_loop is None:
        _feedback_loop = FeedbackLoop()
    return _feedback_loop


def augment_predictions_with_feedback(
    query: str,
    rag_skills: Optional[list[str]] = None,
    rag_tools: Optional[list[str]] = None,
) -> dict[str, list[tuple[str, float]]]:
    """
    Convenience function to get augmented predictions using the global feedback loop.

    This is the main entry point for the feedback loop integration.
    Call this instead of just using RAG predictions to get better results
    that incorporate learned patterns from past observations.

    Args:
        query: Natural language description (e.g., step description)
        rag_skills: Skills predicted by RAG
        rag_tools: Tools predicted by RAG

    Returns:
        Dict with 'skills' and 'tools' containing augmented predictions.
    """
    return get_feedback_loop().get_augmented_predictions(
        query=query,
        rag_skills=rag_skills,
        rag_tools=rag_tools,
    )


def format_rollup_report(rollup: CapabilityRollup, top_keywords: int = 10) -> str:
    """
    Format a human-readable rollup report.

    Shows top keywords and their associated capabilities.
    """
    lines = [
        "=== Capability Rollup Report ===",
        f"Total Observations: {rollup.total_observations}",
        f"Unique Keywords: {len(rollup.keyword_observations)}",
        f"Unique Skills: {len(rollup.skill_totals)}",
        f"Unique Tools: {len(rollup.tool_totals)}",
        "",
    ]

    # Sort keywords by observation count
    sorted_keywords = sorted(
        rollup.keyword_observations.items(),
        key=lambda x: x[1],
        reverse=True
    )[:top_keywords]

    if sorted_keywords:
        lines.append("--- Top Keywords (by frequency) ---")
        for kw, count in sorted_keywords:
            lines.append(f"\n'{kw}' ({count} observations):")

            # Show skill associations
            skill_probs = rollup.get_skill_probabilities(kw)[:3]
            if skill_probs:
                skill_str = ", ".join(f"{s}: {p:.0%}" for s, p in skill_probs)
                lines.append(f"  Skills: {skill_str}")

            # Show tool associations
            tool_probs = rollup.get_tool_probabilities(kw)[:3]
            if tool_probs:
                tool_str = ", ".join(f"{t}: {p:.0%}" for t, p in tool_probs)
                lines.append(f"  Tools: {tool_str}")
    else:
        lines.append("No keyword patterns recorded yet.")

    return "\n".join(lines)
