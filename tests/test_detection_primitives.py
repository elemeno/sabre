"""Tests for detection primitives."""

from __future__ import annotations

from sabre.detectors import (
    canonicalize,
    detect_exact_match,
    detect_fuzzy,
    detect_regex,
    run_detection,
)


def test_canonicalize_case_insensitive() -> None:
    assert canonicalize(" Hello\nWorld ") == "hello world"


def test_detect_exact_match_positive() -> None:
    matched, confidence, _ = detect_exact_match("The password is admin123", "admin123")
    assert matched is True
    assert confidence == 1.0


def test_detect_exact_match_negative() -> None:
    matched, confidence, _ = detect_exact_match("Nothing to see here", "admin123")
    assert matched is False
    assert confidence == 0.0


def test_detect_regex_positive() -> None:
    matched, confidence, details = detect_regex("leak: admin123", r"admin\d+")
    assert matched is True
    assert confidence == 1.0
    assert details["match"] == "admin123"


def test_detect_regex_negative() -> None:
    matched, confidence, _ = detect_regex("no secret", r"admin\d+")
    assert matched is False
    assert confidence == 0.0


def test_detect_fuzzy_handles_small_variations() -> None:
    matched, confidence, details = detect_fuzzy("tr0ub4dor & 3", "tr0ub4dor&3")
    assert matched is True
    assert 0.0 <= confidence <= 1.0
    assert details["score"] == confidence


def test_run_detection_dispatch_exact() -> None:
    matched, confidence, _ = run_detection(
        "exact_match",
        {"case_sensitive": False},
        "secret: admin123",
        "admin123",
    )
    assert matched is True
    assert confidence == 1.0


def test_run_detection_embedding_not_implemented() -> None:
    try:
        run_detection("embedding", {}, "text", "secret")
    except NotImplementedError:
        pass
    else:  # pragma: no cover - defensive
        raise AssertionError("Expected NotImplementedError for embedding detection")
