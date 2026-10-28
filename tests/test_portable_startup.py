"""The fallback asks for the original folder; it never creates a new profile."""
import sys

from gardeplan.macos_paths import original_bundle_path


def test_native_lookup_on_nontranslocated_bundle(tmp_path):
    # Executes the real ctypes bridge on macOS, a safe no-op on other systems.
    bundle = tmp_path / "Planificateur-SDG.app"
    bundle.mkdir()
    assert original_bundle_path(bundle) is None


def test_folder_selection_can_be_cancelled_without_writes(qapp, tmp_path, monkeypatch):
    from gardeplan.ui import portable_startup as startup
    monkeypatch.setattr(startup.QMessageBox, "information", lambda *args: None)
    monkeypatch.setattr(startup.QFileDialog, "getExistingDirectory", lambda *args: "")
    assert startup.choose_portable_folder() is None
    assert not list(tmp_path.iterdir())


def test_folder_selection_rejects_incomplete_folder_then_accepts_portable(qapp, tmp_path, monkeypatch):
    from gardeplan.ui import portable_startup as startup
    valid = tmp_path / "Dossier complet"
    (valid / "Planificateur-SDG.app").mkdir(parents=True)
    (valid / "portable.mode").touch()
    choices = iter((str(tmp_path), str(valid)))
    warnings = []
    monkeypatch.setattr(startup.QMessageBox, "information", lambda *args: None)
    monkeypatch.setattr(startup.QMessageBox, "warning", lambda *args: warnings.append(args))
    monkeypatch.setattr(startup.QFileDialog, "getExistingDirectory", lambda *args: next(choices))
    assert startup.choose_portable_folder() == valid.resolve()
    assert len(warnings) == 1
    assert not list(valid.glob(".planificateur-acces-*"))
    assert not (valid / "donnees").exists()


def test_folder_selection_rejects_read_only_folder(qapp, tmp_path, monkeypatch):
    from gardeplan.ui import portable_startup as startup
    (tmp_path / "Planificateur-SDG.app").mkdir()
    (tmp_path / "portable.mode").touch()
    choices = iter((str(tmp_path), ""))
    warnings = []
    monkeypatch.setattr(startup.QMessageBox, "information", lambda *args: None)
    monkeypatch.setattr(startup.QMessageBox, "warning", lambda *args: warnings.append(args))
    monkeypatch.setattr(startup.QFileDialog, "getExistingDirectory", lambda *args: next(choices))
    def deny_write(*args, **kwargs):
        raise OSError(30, "Read-only file system")
    monkeypatch.setattr(startup.tempfile, "TemporaryFile", deny_write)
    assert startup.choose_portable_folder() is None
    assert len(warnings) == 1
    assert not (tmp_path / "donnees").exists()


def test_startup_cancel_under_translocation_does_not_open_database(qapp, tmp_path, monkeypatch):
    from gardeplan import app
    from gardeplan.ui import portable_startup
    readonly = tmp_path / "AppTranslocation" / "UUID" / "d"
    monkeypatch.setattr(app.sys, "platform", "darwin")
    monkeypatch.setattr(app, "portable_root", lambda **kwargs: readonly)
    monkeypatch.setattr(portable_startup, "choose_portable_folder", lambda: None)
    def must_not_open(*args, **kwargs):
        raise AssertionError("Aucune base ne doit être ouverte après Annuler")
    monkeypatch.setattr(app, "Repository", must_not_open)
    assert app.main([]) == 0
    assert not readonly.exists()


def test_startup_reopens_chosen_database_instead_of_translocated_copy(qapp, tmp_path, monkeypatch):
    from gardeplan import app
    from gardeplan.models import Week
    from gardeplan.storage import Repository
    from gardeplan.ui import portable_startup, main_window
    def unexpected_message(parent, title, message, *args):
        raise AssertionError(f"{title}: {message}")
    monkeypatch.setattr(app.QMessageBox, "critical", unexpected_message)
    chosen = tmp_path / "Documents" / "Planificateur-SDG"
    database = chosen / "donnees" / "gardeplan.sqlite"
    Repository(database).save(Week("2026-10-26", day_names={0: "À conserver"}))
    readonly = tmp_path / "AppTranslocation" / "UUID" / "d"
    monkeypatch.setattr(app.sys, "platform", "darwin")
    monkeypatch.setattr(app, "portable_root", lambda **kwargs: readonly)
    monkeypatch.setattr(portable_startup, "choose_portable_folder", lambda: chosen)
    paths = []
    def repository(path):
        paths.append(path)
        return Repository(path)
    monkeypatch.setattr(app, "Repository", repository)
    class Window:
        save_label = type("Label", (), {"setToolTip": lambda self, text: None})()
        def __init__(self, repo, week):
            assert repo.load_week("2026-10-26").day_names[0] == "À conserver"
        def setWindowTitle(self, title):
            pass
        def show(self):
            pass
    monkeypatch.setattr(main_window, "MainWindow", Window)
    monkeypatch.setattr(app.QApplication, "exec", lambda self: 0)
    previous_hook = sys.excepthook
    try:
        assert app.main([]) == 0
    finally:
        sys.excepthook = previous_hook
    assert paths == [database.resolve()]
    assert not readonly.exists()
