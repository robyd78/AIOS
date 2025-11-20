"""State management package (scene manager, etc.)."""

from .scene_manager import (
    SceneState,
    SceneType,
    current_scene,
    detect_scene_type,
    is_continuation,
    record_assistant_action,
    record_turn,
    reset_scene,
    scene_snapshot,
    seed_from_pairs,
    update_scene,
)

__all__ = [
    "SceneState",
    "SceneType",
    "current_scene",
    "detect_scene_type",
    "is_continuation",
    "record_assistant_action",
    "record_turn",
    "reset_scene",
    "scene_snapshot",
    "seed_from_pairs",
    "update_scene",
]
