from __future__ import annotations

import json

import pytest

from momo_fdvs.services.mtn_format_profile import (
    MTN_FORMAT_PROFILE_SHA256,
    MtnFormatProfileError,
    load_bundled_mtn_profile,
    load_profile_bytes,
)

GENUINE_CASH_IN = (
    "Cash In received for GHS 20.00 from SAMPLE SHOP. Current Balance GHS 80.00 "
    "Available Balance GHS 80.00. Transaction ID: 88888888888. Fee charged: GHS 0. "
    "Cash in (Deposit) is a free transaction on MTN Mobile Money. Please do not pay "
    "any fees for it."
)
PASSIVE_COUNTERFEIT = (
    "Cash In for Gh 700.00 from EXAMPLE TRADERS carent bulance.700.04 "
    "avelabil bulance.700.04 ID: 90000000000001 FEE: 00.000"
)


def test_profile_hash_mismatch_fails_closed() -> None:
    with pytest.raises(MtnFormatProfileError) as failure:
        load_profile_bytes(b"{}", expected_sha256="0" * 64)

    assert failure.value.code == "PROFILE_INTEGRITY_FAILURE"


def test_profile_rejects_raw_text_field() -> None:
    profile = load_bundled_mtn_profile()
    payload = json.loads(profile.raw_bytes)
    payload["raw_text"] = "must never be accepted"

    with pytest.raises(MtnFormatProfileError) as failure:
        load_profile_bytes(json.dumps(payload).encode())

    assert failure.value.code == "PROFILE_SCHEMA_INVALID"


def test_bundled_profile_has_reviewed_identity_and_genuine_cash_in_matches() -> None:
    profile = load_bundled_mtn_profile()
    match = profile.match_text(GENUINE_CASH_IN)

    assert profile.profile_sha256 == MTN_FORMAT_PROFILE_SHA256
    assert match.status == "AVAILABLE"
    assert match.anomalous is False
    assert match.similarity is not None
    assert match.threshold is not None
    assert match.similarity >= match.threshold


def test_passive_counterfeit_is_anomalous_without_exposing_signature_identity() -> None:
    profile = load_bundled_mtn_profile()
    match = profile.match_text(PASSIVE_COUNTERFEIT)
    public = match.as_public_dict()

    assert match.status == "AVAILABLE"
    assert match.anomalous is True
    assert match.similarity is not None
    assert match.threshold is not None
    assert match.similarity < match.threshold
    assert match.required_features_missing
    assert "closest_signature_id" not in public
    assert "90000000000001" not in str(public)


def test_profile_rejects_unknown_feature_and_anchor_codes() -> None:
    profile = load_bundled_mtn_profile()
    payload = json.loads(profile.raw_bytes)
    signature = payload["family_profiles"][0]["signatures"][0]

    signature["feature_codes"].append("private_value_feature")
    with pytest.raises(MtnFormatProfileError) as feature_failure:
        load_profile_bytes(json.dumps(payload).encode())
    assert feature_failure.value.code == "PROFILE_SCHEMA_INVALID"

    payload = json.loads(profile.raw_bytes)
    signature = payload["family_profiles"][0]["signatures"][0]
    signature["anchor_order"].append("private_value_anchor")
    with pytest.raises(MtnFormatProfileError) as anchor_failure:
        load_profile_bytes(json.dumps(payload).encode())
    assert anchor_failure.value.code == "PROFILE_SCHEMA_INVALID"
