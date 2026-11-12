from datetime import date

from app.services.context_registry import ContextAsset, ContextRegistry


def asset(version="1.0", definition="Actual - Budget", precedence=1):
    return ContextAsset.create(
        asset_id="variance", asset_type="metric", name="Budget Variance",
        description="Variance", definition=definition, source_reference="test",
        version=version, effective_from=date(2025, 1, 1), business_scope="ALL",
        owner="Finance", precedence=precedence,
    )


def test_draft_requires_explicit_approval(tmp_path):
    registry = ContextRegistry(tmp_path / "registry.json")
    registry.save(asset())
    assert registry.applicable("metric", date(2025, 2, 1)) == []
    approved = registry.approve("variance", "1.0", "Finance Owner")
    assert approved.approval_status == "approved"
    assert registry.applicable("metric", date(2025, 2, 1))[0].owner == "Finance Owner"


def test_conflicting_equal_precedence_definitions_are_flagged(tmp_path):
    registry = ContextRegistry(tmp_path / "registry.json")
    registry.save(asset())
    registry.save(asset("2.0", "Budget - Actual"))
    registry.approve("variance", "1.0", "Finance")
    registry.approve("variance", "2.0", "Finance")
    assert len(registry.conflicts()) == 1
