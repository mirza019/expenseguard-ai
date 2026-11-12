"""Governed, versioned financial context assets with explicit human approval."""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ContextAsset(BaseModel):
    """One immutable version of a business definition or financial rule."""

    model_config = ConfigDict(extra="forbid")

    asset_id: str
    asset_type: Literal["metric", "glossary", "mapping", "policy", "process"]
    name: str
    description: str
    definition: str
    source_reference: str
    version: str
    effective_from: date
    effective_to: date | None = None
    business_scope: str = "ALL"
    owner: str
    approval_status: Literal["draft", "approved", "rejected"] = "draft"
    precedence: int = Field(default=0, ge=0)
    last_validated_at: datetime | None = None
    content_hash: str

    @classmethod
    def create(cls, **values) -> "ContextAsset":
        canonical = json.dumps(
            {
                key: str(value)
                for key, value in values.items()
                if key not in {"content_hash", "last_validated_at"}
            },
            sort_keys=True,
        )
        values["content_hash"] = hashlib.sha256(canonical.encode()).hexdigest()
        return cls(**values)


class ContextRegistry:
    """Small local registry. Draft extraction never becomes authoritative automatically."""

    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def list(self) -> list[ContextAsset]:
        if not self.path.exists():
            return []
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        return [ContextAsset.model_validate(item) for item in payload]

    def save(self, asset: ContextAsset) -> None:
        assets = self.list()
        identity = (asset.asset_id, asset.version)
        if identity in {(item.asset_id, item.version) for item in assets}:
            raise ValueError("This context asset version already exists.")
        assets.append(asset)
        self._write(assets)

    def approve(self, asset_id: str, version: str, owner: str) -> ContextAsset:
        assets = self.list()
        selected = None
        for index, asset in enumerate(assets):
            if (asset.asset_id, asset.version) == (asset_id, version):
                selected = asset.model_copy(
                    update={
                        "approval_status": "approved",
                        "owner": owner,
                        "last_validated_at": datetime.now(timezone.utc),
                    }
                )
                assets[index] = selected
                break
        if selected is None:
            raise ValueError("Unknown context asset version.")
        self._write(assets)
        return selected

    def applicable(
        self, asset_type: str, when: date, scope: str = "ALL"
    ) -> list[ContextAsset]:
        matches = [
            asset
            for asset in self.list()
            if asset.asset_type == asset_type
            and asset.approval_status == "approved"
            and asset.effective_from <= when
            and (asset.effective_to is None or when <= asset.effective_to)
            and asset.business_scope in {"ALL", scope}
        ]
        return sorted(matches, key=lambda item: (item.precedence, item.version), reverse=True)

    def conflicts(self) -> list[tuple[ContextAsset, ContextAsset]]:
        approved = [item for item in self.list() if item.approval_status == "approved"]
        conflicts = []
        for index, left in enumerate(approved):
            for right in approved[index + 1 :]:
                overlaps = left.effective_to is None or right.effective_from <= left.effective_to
                if (
                    left.asset_type == right.asset_type
                    and left.name.casefold() == right.name.casefold()
                    and left.business_scope == right.business_scope
                    and overlaps
                    and left.definition != right.definition
                    and left.precedence == right.precedence
                ):
                    conflicts.append((left, right))
        return conflicts

    def _write(self, assets: list[ContextAsset]) -> None:
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps([item.model_dump(mode="json") for item in assets], indent=2),
            encoding="utf-8",
        )
        temporary.replace(self.path)


def seed_default_context(registry: ContextRegistry) -> None:
    """Create transparent draft definitions only when the registry is empty."""
    if registry.list():
        return
    registry.save(
        ContextAsset.create(
            asset_id="metric-budget-variance",
            asset_type="metric",
            name="Budget Variance",
            description="Difference between recorded actual expense and represented budget.",
            definition="Actual Cost - Budget",
            source_reference="FinContext built-in draft",
            version="1.0",
            effective_from=date(2020, 1, 1),
            business_scope="ALL",
            owner="Finance",
            approval_status="draft",
            precedence=10,
        )
    )
