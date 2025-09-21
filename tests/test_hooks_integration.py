from __future__ import annotations

import importlib
import sys
import textwrap

import pytest

from sabre.domain.config import ModelCfg
from sabre.infrastructure.adapters.base import AdapterValidationError
from sabre.infrastructure.adapters.registry import create_adapter


@pytest.fixture
def hook_package(tmp_path, monkeypatch) -> str:
    pkg = tmp_path / "tmp_hooks"
    pkg.mkdir()
    (pkg / "__init__.py").write_text(
        textwrap.dedent(
            """
            from typing import Optional


            def preprocess(
                system: Optional[str],
                history: list[dict],
                persona_system: Optional[str],
                runtime: Optional[dict],
            ):
                new_history = list(history)
                new_history.append({"role": "user", "content": "HOOKED"})
                return system, new_history, persona_system, runtime


            def postprocess(text: str) -> str:
                return text.upper()
            """
        ),
        encoding="utf-8",
    )
    sys.modules.pop("tmp_hooks", None)
    monkeypatch.syspath_prepend(str(tmp_path))
    importlib.invalidate_caches()
    return "tmp_hooks"


def _make_model_cfg(tmp_path, **extra) -> ModelCfg:
    return ModelCfg(
        path=tmp_path / "model.yaml",
        name="dummy-model",
        adapter="dummy",
        model_id="dummy",
        **extra,
    )


def test_postprocess_hook_applies(tmp_path, hook_package):
    cfg = _make_model_cfg(tmp_path, postprocess=f"{hook_package}:postprocess")
    adapter = create_adapter("dummy", cfg)
    history = [{"role": "user", "content": "hello"}]
    result = adapter.send(system=None, history=history)
    assert result == "[DUMMY] HELLO"


def test_preprocess_hook_modifies_history(tmp_path, hook_package):
    cfg = _make_model_cfg(tmp_path, preprocess=f"{hook_package}:preprocess")
    adapter = create_adapter("dummy", cfg)
    history = [{"role": "user", "content": "hi"}]
    result = adapter.send(system=None, history=history)
    assert result == "[dummy] HOOKED"


def test_missing_hook_function_raises(tmp_path, hook_package):
    cfg = _make_model_cfg(tmp_path, preprocess=f"{hook_package}:does_not_exist")
    with pytest.raises(AdapterValidationError):
        create_adapter("dummy", cfg)
