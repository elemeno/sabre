"""Tests for utility helpers."""

from __future__ import annotations

from saber.utils import redact_possible_secrets


def test_redact_masks_aws_access_key() -> None:
    raw = "User provided key AKIA1234567890ABCD should be hidden"
    redacted = redact_possible_secrets(raw)
    assert "AKIA1234567890ABCD" not in redacted
    assert "***REDACTED***" in redacted
