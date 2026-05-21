import pytest

from app.runner.pickup_safety import PickupSafety, PickupSafetySnapshot


def _safety(
    snapshot: PickupSafetySnapshot,
    max_concurrent_claims: int = 1,
    max_stale_claims: int = 0,
    max_orphaned_claims: int = 0,
    max_invalid_claims: int = 0,
    max_pickup_retries: int = 2,
) -> PickupSafety:
    async def snapshot_provider() -> PickupSafetySnapshot:
        return snapshot

    return PickupSafety(
        runner_id="runner-test",
        runtime_id="runtime-test",
        max_concurrent_claims=max_concurrent_claims,
        max_stale_claims=max_stale_claims,
        max_orphaned_claims=max_orphaned_claims,
        max_invalid_claims=max_invalid_claims,
        max_pickup_retries=max_pickup_retries,
        retry_window_seconds=300,
        snapshot_provider=snapshot_provider,
    )


@pytest.mark.asyncio
async def test_pickup_safety_allows_clean_snapshot():
    result = await _safety(PickupSafetySnapshot()).inspect()

    assert result.status == "safe"
    assert result.allows_pickup is True
    assert result.duplicate_prevention is True
    assert result.race_condition_controlled is True
    assert result.ownership_consistent is True
    assert result.runtime_consistent is True


@pytest.mark.asyncio
async def test_pickup_safety_blocks_duplicate_active_claims():
    result = await _safety(PickupSafetySnapshot(active_claims=1)).inspect()

    assert result.status == "blocked"
    assert result.allows_pickup is False
    assert result.race_condition_controlled is False
    assert "active_claim_limit_reached" in result.reasons


@pytest.mark.asyncio
async def test_pickup_safety_blocks_stale_claims_above_limit():
    result = await _safety(PickupSafetySnapshot(stale_claims=1)).inspect()

    assert result.status == "blocked"
    assert result.runtime_consistent is False
    assert "stale_claim_limit_reached" in result.reasons


@pytest.mark.asyncio
async def test_pickup_safety_detects_invalid_ownership():
    snapshot = PickupSafetySnapshot(orphaned_claims=1, invalid_claims=1)

    result = await _safety(snapshot).inspect()

    assert result.status == "blocked"
    assert result.ownership_consistent is False
    assert result.duplicate_prevention is False
    assert "orphaned_claims_detected" in result.reasons
    assert "invalid_claims_detected" in result.reasons


@pytest.mark.asyncio
async def test_pickup_safety_limits_pickup_retries():
    safety = _safety(PickupSafetySnapshot(), max_pickup_retries=2)
    safety.record_pickup_retry("conflict")
    safety.record_pickup_retry("conflict")

    result = await safety.inspect()

    assert result.status == "blocked"
    assert result.retry_allowed is False
    assert result.pickup_retry_attempts == 2
    assert "pickup_retry_limit_reached" in result.reasons


@pytest.mark.asyncio
async def test_pickup_safety_contains_snapshot_errors():
    async def broken_snapshot() -> PickupSafetySnapshot:
        raise RuntimeError("snapshot unavailable")

    safety = PickupSafety(snapshot_provider=broken_snapshot)

    result = await safety.inspect()

    assert result.status == "error"
    assert result.allows_pickup is False
    assert result.error == "snapshot unavailable"
    assert "pickup_safety_snapshot_failed" in result.reasons
