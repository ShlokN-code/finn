"""A dossier with every section present and marked 'building' — what a build publishes first, and the base every
stage fills in. Keeping all sections present from the first response is what keeps the contract stable."""

from __future__ import annotations

from datetime import datetime

from finn.models.research import (
    AnalystsSection,
    BullBearSection,
    Dossier,
    DriversSection,
    ExchangeDataSection,
    LedgerSection,
    RedFlagsSection,
    SectionMeta,
    SeriesSection,
    SnapshotSection,
    TrajectorySection,
)

SECTIONS = (
    "snapshot", "trajectory", "ledger", "cash_quality", "balance_sheet", "analysts", "red_flags", "bull_bear",
    "drivers", "exchange_data",
)  # fmt: skip


def building(note: str | None = None) -> SectionMeta:
    return SectionMeta(status="building", reason="not_built_yet", note=note)


def empty_dossier(symbol: str, name: str, now: datetime) -> Dossier:
    return Dossier(
        symbol=symbol,
        name=name,
        template="standard",
        as_of=now,
        built_at=now,
        snapshot=SnapshotSection(meta=building()),
        trajectory=TrajectorySection(meta=building()),
        ledger=LedgerSection(meta=building()),
        cash_quality=SeriesSection(meta=building()),
        balance_sheet=SeriesSection(meta=building()),
        analysts=AnalystsSection(meta=building()),
        red_flags=RedFlagsSection(meta=building()),
        bull_bear=BullBearSection(meta=building()),
        drivers=DriversSection(meta=building()),
        exchange_data=ExchangeDataSection(meta=building()),
    )
