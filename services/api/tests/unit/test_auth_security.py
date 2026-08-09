from __future__ import annotations

import uuid

import pytest

from momo_fdvs.security.passwords import (
    hash_password,
    needs_rehash,
    validate_password,
    verify_password,
)
from momo_fdvs.security.tokens import (
    InvalidAccessToken,
    decode_access_token,
    encode_access_token,
    opaque_token,
    token_hash,
)


def test_argon2_password_round_trip_and_policy() -> None:
    encoded = hash_password("Correct-Horse-Battery-7")
    assert encoded.startswith("$argon2id$")
    assert verify_password(encoded, "Correct-Horse-Battery-7") is True
    assert verify_password(encoded, "incorrect-password") is False
    assert verify_password("not-a-password-hash", "anything") is False
    assert needs_rehash("not-a-password-hash") is True
    assert needs_rehash(encoded) is False
    with pytest.raises(ValueError, match="between 12 and 256"):
        validate_password("too-short")
    with pytest.raises(ValueError, match="between 12 and 256"):
        validate_password("x" * 257)


def test_access_and_opaque_token_security() -> None:
    user_id = uuid.uuid4()
    signing_fixture_value = "unit-test-secret-that-is-at-least-32-characters"
    token = encode_access_token(
        user_id=user_id,
        roles={"USER"},
        token_version=3,
        secret=signing_fixture_value,
        ttl_minutes=1,
    )
    claims = decode_access_token(token, signing_fixture_value)
    assert claims.user_id == user_id
    assert claims.roles == frozenset({"USER"})
    assert claims.token_version == 3
    with pytest.raises(InvalidAccessToken):
        decode_access_token(token + "altered", signing_fixture_value)

    expired = encode_access_token(
        user_id=user_id,
        roles={"USER"},
        token_version=3,
        secret=signing_fixture_value,
        ttl_minutes=-1,
    )
    with pytest.raises(InvalidAccessToken):
        decode_access_token(expired, signing_fixture_value)

    first = opaque_token()
    second = opaque_token()
    assert first != second
    assert len(first) >= 64
    assert token_hash(first, signing_fixture_value) == token_hash(first, signing_fixture_value)
    assert token_hash(first, signing_fixture_value) != token_hash(second, signing_fixture_value)
