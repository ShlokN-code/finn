"""Shared data contracts. Mirrored to web/lib/types.ts by `python -m finn.models.export_schema`."""

from finn.models.common import (
    Basis,
    Category,
    Citation,
    Claim,
    Figure,
    Impact,
    Period,
    SourceType,
    Unit,
    VerificationStatus,
)
from finn.models.core import (
    Alert,
    Card,
    Dossier,
    DossierSection,
    Driver,
    Event,
    EventStage,
    Filing,
    Holding,
    MoveExplanation,
    Promise,
    ScoreBreakdown,
    Series,
    TimelineItem,
)

# Top-level contracts exported to TypeScript (nested types come along via $defs).
EXPORTED = [Citation, Figure, Claim, Period, Filing, Event, Card, Alert, Holding, Driver, Promise, Dossier]

__all__ = [
    "Alert",
    "Basis",
    "Card",
    "Category",
    "Citation",
    "Claim",
    "Dossier",
    "DossierSection",
    "Driver",
    "Event",
    "EventStage",
    "Figure",
    "Filing",
    "Holding",
    "Impact",
    "MoveExplanation",
    "Period",
    "Promise",
    "ScoreBreakdown",
    "Series",
    "SourceType",
    "TimelineItem",
    "Unit",
    "VerificationStatus",
    "EXPORTED",
]
