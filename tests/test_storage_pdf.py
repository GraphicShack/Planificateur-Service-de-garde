from copy import deepcopy
import socket
import sqlite3
from pathlib import Path
import pytest
from gardeplan.storage import Repository
from gardeplan.pdf import export_general, export_individual, export_combined, export_all_individual


def test_save_reopen_exact_minutes_and_named_day(valid_week, tmp_path):
    path = tmp_path / 'planning.sqlite'
    repo = Repository(path)
    version = repo.save(valid_week)
    restored = Repository(path).load_week(valid_week.monday)
    assert restored.to_dict() == valid_week.to_dict()
    assert restored.day_names == valid_week.day_names
    assert repo.load_version(version).shifts[0].start == 410


def test_published_version_is_frozen_when_new_draft_saved(valid_week, tmp_path):
    repo = Repository(tmp_path / 'planning.sqlite')
    valid_week.status = 'published'
    published_id = repo.save(valid_week)
    draft = deepcopy(valid_week)
    draft.status = 'draft'
    draft.educators[0].name = 'Nouveau nom'
    draft.day_names = {0: 'Nouvelle désignation'}
    repo.save(draft)
    old = repo.load_version(published_id)
    assert old.status == 'published'
    assert old.educators[0].name == 'Marie Tremblay'
    assert old.day_names == valid_week.day_names
    assert len(repo.history(valid_week.monday)) == 2


def test_invalid_publication_refused_but_draft_allowed(valid_week, tmp_path):
    repo = Repository(tmp_path / 'planning.sqlite')
    valid_week.shifts.pop()
    valid_week.status = 'published'
    with pytest.raises(ValueError):
        repo.save(valid_week)
    valid_week.status = 'draft'
    repo.save(valid_week)
    assert repo.load_week(valid_week.monday).status == 'draft'


def test_archival_and_restore_create_new_version(valid_week, tmp_path):
    repo = Repository(tmp_path / 'planning.sqlite')
    valid_week.status = 'archived'
    archive_id = repo.save(valid_week)
    archived = repo.load_version(archive_id)
    restored = repo.restore(archive_id)
    assert restored.status == 'draft'
    assert repo.load_version(archive_id).to_dict() == archived.to_dict()
    assert len(repo.history(valid_week.monday)) == 2


def test_duplicate_changes_week_and_preserves_exact_schedule(valid_week, tmp_path):
    repo = Repository(tmp_path / 'planning.sqlite')
    repo.save(valid_week)
    duplicate = repo.duplicate(valid_week, '2026-11-02')
    assert duplicate.monday == '2026-11-02'
    assert duplicate.status == 'draft'
    assert [(s.start, s.end) for s in duplicate.shifts] == [(410, 1055), (410, 1055)]
    assert repo.load_week('2026-10-26').monday == '2026-10-26'


def test_local_backup_import_and_corruption_refusal(valid_week, tmp_path):
    repo = Repository(tmp_path / 'source.sqlite')
    repo.save(valid_week)
    backup = tmp_path / 'backup.gardeplan'
    repo.backup(backup)
    destination = Repository(tmp_path / 'destination.sqlite')
    destination.import_backup(backup)
    assert destination.load_week(valid_week.monday).to_dict() == valid_week.to_dict()
    corrupt = tmp_path / 'corrupt.sqlite'
    corrupt.write_bytes(b'not a sqlite database')
    with pytest.raises((ValueError, sqlite3.DatabaseError, OSError)):
        destination.import_backup(corrupt)
    assert destination.load_week(valid_week.monday).shifts[0].start == 410


def test_all_pdf_exports_are_real_pdf_documents(valid_week, tmp_path):
    general = tmp_path / 'general.pdf'
    individual = tmp_path / 'Marie.pdf'
    combined = tmp_path / 'regroupe.pdf'
    export_general(valid_week, general)
    export_individual(valid_week, 'e1', individual)
    export_combined(valid_week, combined)
    directory = tmp_path / 'individuels'
    directory.mkdir()
    export_all_individual(valid_week, directory)
    outputs = [general, individual, combined, *directory.glob('*.pdf')]
    assert len(outputs) == 5
    for file in outputs:
        content = file.read_bytes()
        assert content.startswith(b'%PDF-')
        assert b'%%EOF' in content[-100:]
        assert len(content) > 500


def test_core_operations_work_with_network_disabled(valid_week, tmp_path, monkeypatch):
    def forbid_network(*args, **kwargs):
        raise AssertionError('Le logiciel a tenté un accès réseau')
    monkeypatch.setattr(socket, 'socket', forbid_network)
    monkeypatch.setattr(socket, 'create_connection', forbid_network)
    from gardeplan.validation import validate
    repo = Repository(tmp_path / 'offline.sqlite')
    repo.save(valid_week)
    restored = repo.load_week(valid_week.monday)
    assert not [i for i in validate(restored) if i.severity == 'error']
    export_general(restored, tmp_path / 'offline.pdf')
    repo.backup(tmp_path / 'offline-backup.sqlite')
    assert (tmp_path / 'offline.pdf').exists()


def test_database_prevents_modifying_or_deleting_old_versions(valid_week, tmp_path):
    path = tmp_path / 'immutable.sqlite'
    repo = Repository(path)
    version = repo.save(valid_week)
    with sqlite3.connect(path) as connection:
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute('UPDATE versions SET status=? WHERE id=?', ('archived', version))
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute('DELETE FROM versions WHERE id=?', (version,))
    assert repo.load_version(version).status == 'draft'


def test_import_rejects_tampered_snapshot_before_replacing_database(valid_week, tmp_path):
    source = Repository(tmp_path / 'source.sqlite')
    source.save(valid_week)
    tampered = tmp_path / 'tampered.sqlite'
    source.backup(tampered)
    with sqlite3.connect(tampered) as connection:
        connection.execute('DROP TRIGGER versions_no_update')
        connection.execute("UPDATE versions SET payload=replace(payload, 'Marie', 'Sophie')")
    destination = Repository(tmp_path / 'destination.sqlite')
    destination.save(valid_week)
    with pytest.raises(ValueError):
        destination.import_backup(tampered)
    assert destination.load_week(valid_week.monday).educators[0].name == 'Marie Tremblay'


def test_pdf_contains_named_day_and_exact_times(valid_week, tmp_path):
    pypdf = pytest.importorskip('pypdf')
    general = tmp_path / 'general.pdf'
    individual = tmp_path / 'individual.pdf'
    export_general(valid_week, general)
    export_individual(valid_week, 'e1', individual)
    general_text = '\n'.join(page.extract_text() for page in pypdf.PdfReader(general).pages)
    individual_text = '\n'.join(page.extract_text() for page in pypdf.PdfReader(individual).pages)
    assert 'Halloween' in general_text
    assert 'Halloween' in individual_text
    assert '06 h 50' in individual_text
    assert '17 h 35' in individual_text
    assert '10 h 45' in individual_text
