"""Le même diagnostic est exécuté dans le binaire gelé pendant la livraison."""
import json

import pytest

from gardeplan.installation_check import check_installation


def test_missing_runtime_dependency_never_returns_a_success(tmp_path, monkeypatch):
    import builtins

    original_import = builtins.__import__

    def reject_qt(name, *args, **kwargs):
        if name == "PySide6" or name.startswith("PySide6."):
            raise ImportError("Dépendance Qt absente pour ce test")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", reject_qt)
    result = tmp_path / "diagnostic.json"
    result.write_text('{"success":true}', encoding="utf-8")
    assert check_installation(result) == 1
    report = json.loads(result.read_text(encoding="utf-8"))
    assert report["success"] is False
    assert report["checks"] == {}
    assert "Qt absente" in report["error"]


def test_diagnostic_file_failure_returns_nonzero(tmp_path, monkeypatch):
    import builtins
    original_import = builtins.__import__

    def reject_qt(name, *args, **kwargs):
        if name.startswith("PySide6"):
            raise ImportError("Qt non chargé")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", reject_qt)
    target = tmp_path / "dossier"
    target.mkdir()
    assert check_installation(target) == 1
    assert target.is_dir()
    assert not list(tmp_path.glob("verification-*.tmp"))
