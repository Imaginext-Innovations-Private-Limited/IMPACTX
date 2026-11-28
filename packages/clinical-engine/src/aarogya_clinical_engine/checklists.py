"""Deterministic NHM ASHA maternal ANC & postnatal (HBNC) checklist evaluator."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import date
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from aarogya_clinical_engine.rules_loader import load_maternal_anc_rules
from aarogya_contracts import (
    ActionCard,
    ActionCardPriority,
    NodeTier,
    TriageSeverity,
    WatchMode,
)


class ChecklistType(StrEnum):
    """Supported NHM ASHA antenatal and postnatal checklists."""

    ANC_TRIMESTER_1 = "anc_trimester_1"
    ANC_TRIMESTER_2 = "anc_trimester_2"
    ANC_TRIMESTER_3 = "anc_trimester_3"
    PNC_MOTHER = "pnc_mother"
    PNC_NEWBORN = "pnc_newborn"


class ChecklistEvaluation(BaseModel):
    """Deterministic evaluation output for a maternal or postnatal checklist."""

    model_config = ConfigDict(extra="forbid")

    checklist_type: ChecklistType
    title: str
    protocol: str
    patient_id: str | None = None
    total_items: int = Field(..., ge=1)
    completed_items: list[str] = Field(default_factory=list)
    missing_items: list[str] = Field(default_factory=list)
    missing_critical_checks: list[str] = Field(default_factory=list)
    missing_critical_labels: list[str] = Field(default_factory=list)
    completion_score: float = Field(..., ge=0.0, le=1.0)
    is_complete: bool
    has_critical_gaps: bool
    action_cards: list[ActionCard] = Field(default_factory=list)


def list_checklist_types() -> list[ChecklistType]:
    """Return all supported maternal and postnatal checklist identifiers."""
    return list(ChecklistType)


def get_checklist_definition(checklist_type: ChecklistType | str) -> dict[str, Any]:
    """Return the raw JSON definition for a checklist type."""
    key = ChecklistType(checklist_type).value
    checklists: dict[str, Any] = load_maternal_anc_rules()["checklists"]
    if key not in checklists:
        raise KeyError(f"Unknown checklist type: {key}")
    return dict(checklists[key])


def select_anc_checklist_for_gestational_weeks(gestational_weeks: int) -> ChecklistType:
    """Map gestational age in weeks to the corresponding NHM ANC trimester checklist."""
    if gestational_weeks < 0 or gestational_weeks > 45:
        raise ValueError(f"gestational_weeks must be between 0 and 45, got {gestational_weeks}")
    if gestational_weeks <= 12:
        return ChecklistType.ANC_TRIMESTER_1
    if gestational_weeks <= 27:
        return ChecklistType.ANC_TRIMESTER_2
    return ChecklistType.ANC_TRIMESTER_3


def _normalize_completed_ids(
    completed: Iterable[str] | Mapping[str, bool],
) -> set[str]:
    if isinstance(completed, Mapping):
        return {str(k).strip() for k, done in completed.items() if bool(done)}
    return {str(item_id).strip() for item_id in completed if str(item_id).strip()}


def evaluate_checklist(
    checklist_type: ChecklistType | str,
    completed_checks: Iterable[str] | Mapping[str, bool],
    *,
    patient_id: str | None = None,
    due_by: date | None = None,
    target_tier: NodeTier = NodeTier.TIER_0_WATCH,
    watch_mode: WatchMode | None = WatchMode.CHW_COMPANION,
) -> ChecklistEvaluation:
    """Evaluate ANC trimester or HBNC postnatal checklist completion and emit ActionCards."""
    resolved_type = ChecklistType(checklist_type)
    definition = get_checklist_definition(resolved_type)
    items: list[dict[str, Any]] = definition["items"]
    completed_set = _normalize_completed_ids(completed_checks)

    completed_ids: list[str] = []
    missing_ids: list[str] = []
    missing_critical_ids: list[str] = []
    missing_critical_labels: list[str] = []
    missing_routine_items: list[dict[str, Any]] = []
    action_cards: list[ActionCard] = []

    effective_watch_mode = watch_mode if target_tier == NodeTier.TIER_0_WATCH else None

    for item in items:
        item_id = str(item["id"])
        if item_id in completed_set:
            completed_ids.append(item_id)
            continue

        missing_ids.append(item_id)
        if bool(item.get("critical", False)):
            missing_critical_ids.append(item_id)
            missing_critical_labels.append(str(item["label"]))
            severity = TriageSeverity(item.get("escalation_severity", "YELLOW_PHC"))
            action_cards.append(
                ActionCard(
                    patient_id=patient_id,
                    title=f"Missing Critical Check: {item['label']}"[:160],
                    summary=f"{definition['title']} — critical check pending: {item['label']}.",
                    action_steps=[str(item["recommended_action"])],
                    priority=ActionCardPriority.HIGH,
                    severity=severity,
                    target_tier=target_tier,
                    watch_mode=effective_watch_mode,
                    due_by=due_by,
                )
            )
        else:
            missing_routine_items.append(item)

    if missing_routine_items:
        action_cards.append(
            ActionCard(
                patient_id=patient_id,
                title=f"Pending Routine Checks ({len(missing_routine_items)})",
                summary=f"{definition['title']} has {len(missing_routine_items)} routine check(s) remaining.",
                action_steps=[str(item["recommended_action"]) for item in missing_routine_items],
                priority=ActionCardPriority.LOW,
                severity=TriageSeverity.GREEN_HOME,
                target_tier=target_tier,
                watch_mode=effective_watch_mode,
                due_by=due_by,
            )
        )

    total = len(items)
    score = round(len(completed_ids) / total, 4)

    return ChecklistEvaluation(
        checklist_type=resolved_type,
        title=str(definition["title"]),
        protocol=str(definition["protocol"]),
        patient_id=patient_id,
        total_items=total,
        completed_items=completed_ids,
        missing_items=missing_ids,
        missing_critical_checks=missing_critical_ids,
        missing_critical_labels=missing_critical_labels,
        completion_score=score,
        is_complete=len(missing_ids) == 0,
        has_critical_gaps=len(missing_critical_ids) > 0,
        action_cards=action_cards,
    )
