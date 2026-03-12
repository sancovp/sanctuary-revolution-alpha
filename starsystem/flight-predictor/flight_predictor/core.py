"""
Capability Predictor - Library Facade

This is the main entry point for using capability prediction as a library.
It re-exports the core functions and models for easy access.

Usage:
    from capability_predictor.core import (
        predict_capabilities,
        format_capability_prediction,
        CapabilityObservation,
        PlanStep,
    )

    # Create observation
    obs = CapabilityObservation(
        steps=[
            PlanStep(step_number=1, description="Plan the project structure"),
            PlanStep(step_number=2, description="Implement core logic"),
            PlanStep(step_number=3, description="Write tests"),
        ],
        context_domain="PAIAB"
    )

    # Get predictions
    prediction = predict_capabilities(obs)

    # Format for display
    print(format_capability_prediction(prediction))
"""

# Main prediction functions
from .predictor import (
    format_capability_prediction,
    predict_capabilities,
)

# Input models
from .models import (
    CapabilityObservation,
    PlanStep,
)

# Output models (for type hints and inspection)
from .models import (
    CapabilityPrediction,
    PredictedSkill,
    PredictedSkillDomain,
    PredictedSkillset,
    PredictedServer,
    PredictedTool,
    PredictedToolDomain,
    StepPrediction,
)

# Usage tracking (Phase 3)
from .models import ActualUsage
from .tracking import (
    TrackingSession,
    start_tracking_session,
    end_tracking_session,
    record_tool_from_hook,
    get_active_session,
    format_mismatch_report,
    load_all_observations,
    # Mismatch detection (Phase 3.4)
    MismatchAnalysis,
    compute_mismatch_analysis,
    get_improvement_suggestions,
    format_mismatch_analysis_report,
    # Feedback loop integration (Phase 4.1)
    FeedbackLoop,
    get_feedback_loop,
    augment_predictions_with_feedback,
)

# Alias clusters (Phase 4.2)
from .alias_clusters import (
    AliasCluster,
    AliasClustersConfig,
    load_alias_clusters,
    save_alias_clusters,
    reset_alias_clusters_to_defaults,
    match_query_to_domains,
    get_bootstrap_predictions,
    format_bootstrap_predictions,
    augment_with_alias_clusters,
    add_keyword_to_cluster,
    add_skill_to_cluster,
    add_tool_to_cluster,
    list_all_clusters,
    format_clusters_report,
)

# Graph logic matching (ONE Cypher query per type, no N+1)
from .graph_logic import (
    GraphSkillMatch,
    GraphToolMatch,
    GraphFlightMatch,
    UnifiedGraphResult,
    skill_graph_logic_match,
    tool_graph_logic_match,
    flight_graph_logic_match,
    unified_graph_logic_match,
)

# Low-level RAG functions (for advanced usage)
from .skill_rag import (
    SkillRAGResult,
    format_skill_rag_result,
    skill_rag_carton_style,
)
from .tool_rag import (
    ToolRAGResult,
    format_tool_rag_result,
    tool_rag_carton_style,
)

__all__ = [
    # Main API
    "predict_capabilities",
    "format_capability_prediction",
    # Input models
    "CapabilityObservation",
    "PlanStep",
    # Output models
    "CapabilityPrediction",
    "StepPrediction",
    "PredictedSkill",
    "PredictedSkillset",
    "PredictedSkillDomain",
    "PredictedTool",
    "PredictedServer",
    "PredictedToolDomain",
    # Usage tracking
    "ActualUsage",
    "TrackingSession",
    "start_tracking_session",
    "end_tracking_session",
    "record_tool_from_hook",
    "get_active_session",
    "format_mismatch_report",
    "load_all_observations",
    # Mismatch detection (Phase 3.4)
    "MismatchAnalysis",
    "compute_mismatch_analysis",
    "get_improvement_suggestions",
    "format_mismatch_analysis_report",
    # Feedback loop integration (Phase 4.1)
    "FeedbackLoop",
    "get_feedback_loop",
    "augment_predictions_with_feedback",
    # Alias clusters (Phase 4.2)
    "AliasCluster",
    "AliasClustersConfig",
    "load_alias_clusters",
    "save_alias_clusters",
    "reset_alias_clusters_to_defaults",
    "match_query_to_domains",
    "get_bootstrap_predictions",
    "format_bootstrap_predictions",
    "augment_with_alias_clusters",
    "add_keyword_to_cluster",
    "add_skill_to_cluster",
    "add_tool_to_cluster",
    "list_all_clusters",
    "format_clusters_report",
    # Graph logic (whole-graph Cypher assembly)
    "GraphSkillMatch",
    "GraphToolMatch",
    "GraphFlightMatch",
    "UnifiedGraphResult",
    "skill_graph_logic_match",
    "tool_graph_logic_match",
    "flight_graph_logic_match",
    "unified_graph_logic_match",
    # Low-level RAG
    "skill_rag_carton_style",
    "tool_rag_carton_style",
    "format_skill_rag_result",
    "format_tool_rag_result",
    "SkillRAGResult",
    "ToolRAGResult",
]
