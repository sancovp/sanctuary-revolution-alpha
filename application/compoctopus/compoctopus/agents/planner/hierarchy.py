"""PlanHierarchy — Structured task decomposition output."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any


@dataclass
class Task:
    name: str
    description: str


@dataclass
class Deliverable:
    name: str
    tasks: List[Task] = field(default_factory=list)


@dataclass
class Component:
    name: str
    deliverables: List[Deliverable] = field(default_factory=list)


@dataclass
class Feature:
    name: str
    components: List[Component] = field(default_factory=list)


@dataclass
class PlanHierarchy:
    project_name: str
    features: List[Feature] = field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_json(cls, json_str: str) -> "PlanHierarchy":
        data = json.loads(json_str)
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PlanHierarchy":
        features = []
        for feature_data in data.get("features", []):
            components = []
            for comp_data in feature_data.get("components", []):
                deliverables = []
                for deliv_data in comp_data.get("deliverables", []):
                    tasks = [
                        Task(name=t["name"], description=t["description"])
                        for t in deliv_data.get("tasks", [])
                    ]
                    deliverables.append(Deliverable(
                        name=deliv_data["name"],
                        tasks=tasks,
                    ))
                components.append(Component(
                    name=comp_data["name"],
                    deliverables=deliverables,
                ))
            features.append(Feature(
                name=feature_data["name"],
                components=components,
            ))
        return cls(
            project_name=data["project_name"],
            features=features,
        )
