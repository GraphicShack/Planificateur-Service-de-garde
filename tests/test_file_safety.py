"""Failures must preserve the user's previous database and exported documents."""
from pathlib import Path
import sqlite3
import pytest

from gardeplan.models import Week
from gardeplan.storage import Repository, StorageError
from gardeplan.pdf import export_general, PdfError


def test_unrelated_sqlite_file_is_never_modified(tmp_path):
    path = tmp_path / 'autre-application.sqlite'
    with sqlite3.connect(path) as conn:
        conn.execute('CREATE TABLE personnel(nom TEXT)')
        conn.execute("INSERT INTO personnel VALUES ('Donnée conservée')")
    before = path.read_bytes()
    with pytest.raises(StorageError):
        Repository(path)
    assert path.read_bytes() == before


def test_future_database_schema_is_rejected_without_changes(tmp_path):
    path = tmp_path / 'future.sqlite'
    with sqlite3.connect(path) as conn:
        conn.execute('CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT)')
        conn.execute("INSERT INTO metadata VALUES ('schema_version','999')")
        conn.execute('CREATE TABLE future_data (id INTEGER PRIMARY KEY, value TEXT)')
        conn.execute("INSERT INTO future_data VALUES (1,'à conserver')")
    before = path.read_bytes()
    with pytest.raises(StorageError):
        Repository(path)
    assert path.read_bytes() == before


def test_backup_replace_failure_preserves_existing_backup(valid_week, tmp_path, monkeypatch):
    repo = Repository(tmp_path / 'planning.sqlite')
    repo.save(valid_week)
    backup = repo.backup(tmp_path / 'backup.sqlite')
    before = backup.read_bytes()
    valid_week.day_names[0] = 'Modification après sauvegarde'
    repo.save(valid_week)

    def deny_replace(source, destination):
        raise PermissionError('Fichier ouvert par un autre programme')

    monkeypatch.setattr('gardeplan.storage.os.replace', deny_replace)
    with pytest.raises(StorageError):
        repo.backup(backup)
    assert backup.read_bytes() == before
    assert not list(tmp_path.glob('.gardeplan-backup-*'))


def test_import_replace_failure_preserves_open_database(valid_week, tmp_path, monkeypatch):
    incoming = Repository(tmp_path / 'incoming.sqlite')
    incoming.save(valid_week)
    destination = Repository(tmp_path / 'destination.sqlite')
    destination.save(Week(valid_week.monday, day_names={0: 'Données originales'}))
    old_bytes = destination.path.read_bytes()
    real_replace = __import__('os').replace

    def deny_final_replace(source, target):
        if Path(target) == destination.path:
            raise PermissionError('Base verrouillée par un autre programme')
        return real_replace(source, target)

    monkeypatch.setattr('gardeplan.storage.os.replace', deny_final_replace)
    with pytest.raises(StorageError):
        destination.import_backup(incoming.path)
    assert destination.path.read_bytes() == old_bytes
    assert destination.load_week(valid_week.monday).day_names[0] == 'Données originales'
    assert list(tmp_path.glob('destination-avant-import-*.sqlite3'))
    assert not list(tmp_path.glob('.gardeplan-import-*'))


def test_pdf_replace_failure_preserves_existing_document(valid_week, tmp_path, monkeypatch):
    path = export_general(valid_week, tmp_path / 'horaire.pdf')
    before = path.read_bytes()
    valid_week.day_names[0] = 'Nouvelle journée'

    def deny_replace(source, destination):
        raise PermissionError('Document ouvert dans le lecteur PDF')

    monkeypatch.setattr('gardeplan.pdf.os.replace', deny_replace)
    with pytest.raises(PdfError):
        export_general(valid_week, path)
    assert path.read_bytes() == before
    assert not list(tmp_path.glob('.gardeplan-pdf-*'))
