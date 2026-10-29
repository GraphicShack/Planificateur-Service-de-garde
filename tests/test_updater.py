import zipfile
import sys
import pytest
from gardeplan.portable_package import create_archive,extract_package,inspect_archive,sha256,write_manifest,verify_folder
from gardeplan.storage import Repository
from gardeplan.updater import prepare_update,prepare_rollback,refresh_prepared


def bundle(path,version='0.5.0',target='windows'):
    path.mkdir()
    executable='Planificateur-SDG.exe' if target=='windows' else 'Planificateur-SDG.app/Contents/MacOS/Planificateur-SDG'
    binary=path/executable;binary.parent.mkdir(parents=True,exist_ok=True);binary.write_bytes(b'portable '+version.encode())
    binary.chmod(0o755)
    (path/'portable.mode').write_text('portable')
    (path/'donnees').mkdir()
    write_manifest(path,version,target,'x64')
    return path


@pytest.fixture
def update_case(tmp_path):
    from test_home_data import planned_day
    old=bundle(tmp_path/'ancien')
    repository=Repository(old/'donnees/gardeplan.sqlite');repository.save(planned_day())
    (old/'donnees/interface.json').write_text('{"preset":"Bleu"}')
    future=bundle(tmp_path/'fabrication','0.5.1')
    archive=create_archive(future,tmp_path/'nouvelle.zip')
    package=inspect_archive(archive,'0.5.0','windows','x64')
    destination=tmp_path/'versions';destination.mkdir()
    return old,repository,package,destination


def test_update_clones_database_history_and_preferences_without_touching_old_version(update_case):
    old,repo,package,destination=update_case
    before=sha256(repo.path)
    prepared=prepare_update(package,repo,destination,current_root=old,current_version='0.5.0')
    restored=Repository(prepared.folder/'donnees/gardeplan.sqlite')
    assert restored.latest_week()==repo.latest_week()
    assert sha256(repo.path)==before
    assert prepared.executable.is_file() and prepared.version=='0.5.1'
    assert (prepared.folder/'donnees/interface.json').read_text()=='{"preset":"Bleu"}'
    assert (prepared.folder/'retour-avant-maj/gardeplan.sqlite').is_file()
    assert verify_folder(prepared.folder)['version']=='0.5.1'
    another=prepare_update(package,repo,destination,current_root=old)
    assert another.folder!=prepared.folder and prepared.folder.is_dir()


def test_rollback_restores_pre_update_data_and_keeps_newer_work(update_case):
    old,repo,package,destination=update_case
    original=repo.latest_week()
    prepared=prepare_update(package,repo,destination,current_root=old)
    new_repo=Repository(prepared.folder/'donnees/gardeplan.sqlite')
    changed=new_repo.latest_week();changed.day_names[0]='Travail après mise à jour';new_repo.save(changed)
    returned=prepare_rollback(prepared.folder,new_repo,destination)
    assert returned.operation=='rollback' and returned.version=='0.5.0'
    assert Repository(returned.folder/'donnees/gardeplan.sqlite').latest_week()==original
    assert new_repo.latest_week().day_names[0]=='Travail après mise à jour'
    assert Repository(returned.folder/'donnees/sauvegardes/avant-retour.sqlite').latest_week()==changed


def test_refresh_before_launch_captures_final_saved_changes_and_respects_a_running_target(update_case):
    from PySide6.QtCore import QLockFile
    old,repo,package,destination=update_case
    prepared=prepare_update(package,repo,destination,current_root=old)
    modified=repo.latest_week();modified.day_names[0]='Dernière sauvegarde';repo.save(modified)
    refresh_prepared(prepared,repo)
    assert Repository(prepared.folder/'donnees/gardeplan.sqlite').latest_week()==modified
    lock=QLockFile(str(prepared.folder/'donnees/gardeplan.sqlite')+'.lock');assert lock.tryLock(100)
    try:
        with pytest.raises(ValueError):refresh_prepared(prepared,repo)
    finally:lock.unlock()


@pytest.mark.parametrize('target,arch,current',[('macos','x64','0.5.0'),('windows','arm64','0.5.0'),('windows','x64','0.5.1'),('windows','x64','0.6.0')])
def test_wrong_platform_architecture_and_non_newer_versions_are_refused(update_case,target,arch,current):
    _,_,package,_=update_case
    with pytest.raises(ValueError):inspect_archive(package.path,current,target,arch)


@pytest.mark.parametrize('bad_name',['../hors-dossier','Planificateur-SDG/../../hors-dossier','C:/logiciel.exe','Planificateur-SDG/PORTABLE.MODE'])
def test_archive_traversal_and_case_collisions_are_refused(update_case,bad_name):
    _,_,package,_=update_case
    with zipfile.ZipFile(package.path,'a') as archive:archive.writestr(bad_name,b'bad')
    with pytest.raises(ValueError):inspect_archive(package.path,'0.5.0','windows','x64')


def test_corrupted_content_is_rejected_and_leaves_no_partial_version(update_case,tmp_path):
    old,repo,package,destination=update_case
    path=tmp_path/'corrompue.zip'
    with zipfile.ZipFile(package.path) as source,zipfile.ZipFile(path,'w') as output:
        for info in source.infolist():
            value=source.read(info)
            if info.filename.endswith('.exe'):value=b'changed content'
            output.writestr(info,value)
    bad=inspect_archive(path,'0.5.0','windows','x64')
    with pytest.raises(ValueError):prepare_update(bad,repo,destination,current_root=old)
    assert not list(destination.iterdir())
    assert repo.latest_week() is not None


def test_changed_archive_and_destination_inside_source_are_refused(update_case):
    old,repo,package,destination=update_case
    with pytest.raises(ValueError):prepare_update(package,repo,old,current_root=old)
    with zipfile.ZipFile(package.path,'a') as archive:archive.writestr('unexpected',b'data')
    with pytest.raises(ValueError):prepare_update(package,repo,destination,current_root=old)
    assert not list(destination.iterdir())


def test_macos_internal_links_are_preserved_but_external_links_are_refused(tmp_path):
    from gardeplan.portable_package import read_manifest,validate_manifest
    root=bundle(tmp_path/'mac','0.5.1','macos')
    directory=root/'Planificateur-SDG.app/Contents/Resources';directory.mkdir()
    (directory/'version').write_text('data')
    if sys.platform=='win32':
        write_manifest(root,'0.5.1','macos','x64')
        data=read_manifest(root)
        data['links']['Planificateur-SDG.app/Contents/Resources/alias']='version'
        validate_manifest(data)
        data['links']['Planificateur-SDG.app/Contents/Resources/alias']='../../../../hors-dossier'
        with pytest.raises(ValueError):validate_manifest(data)
        return
    (directory/'alias').symlink_to('version')
    write_manifest(root,'0.5.1','macos','x64')
    archive=create_archive(root,tmp_path/'mac.zip')
    package=inspect_archive(archive,'0.5.0','macos','x64')
    extracted=extract_package(package,tmp_path/'extrait')
    assert (extracted/'Planificateur-SDG.app/Contents/Resources/alias').read_text()=='data'
    (directory/'alias').unlink();(directory/'alias').symlink_to('../../../../hors-dossier')
    with pytest.raises(ValueError):write_manifest(root,'0.5.1','macos','x64')


def test_first_launch_resumes_latest_source_data_if_preparation_was_left_for_later(update_case):
    from gardeplan.updater import activate_pending,read_receipt
    old,repo,package,destination=update_case
    prepared=prepare_update(package,repo,destination,current_root=old)
    modified=repo.latest_week();modified.day_names[0]='Travail enregistré plus tard';repo.save(modified)
    activate_pending(prepared.folder)
    assert not read_receipt(prepared.folder)['pending']
    assert Repository(prepared.folder/'donnees/gardeplan.sqlite').latest_week()==modified


def test_pending_update_refuses_to_copy_data_while_the_old_session_is_open(update_case):
    from PySide6.QtCore import QLockFile
    from gardeplan.updater import activate_pending
    old,repo,package,destination=update_case
    prepared=prepare_update(package,repo,destination,current_root=old)
    lock=QLockFile(str(repo.path)+'.lock');assert lock.tryLock(100)
    try:
        with pytest.raises(ValueError):activate_pending(prepared.folder)
    finally:lock.unlock()


def test_user_exports_beside_program_do_not_block_update_or_enter_the_new_package(update_case):
    old,repo,package,destination=update_case
    exported=old/'Horaire-pedagogique.pdf';exported.write_bytes(b'private PDF export')
    prepared=prepare_update(package,repo,destination,current_root=old,current_version='0.5.0')
    restored=prepare_rollback(prepared.folder,Repository(prepared.folder/'donnees/gardeplan.sqlite'),destination)
    assert exported.read_bytes()==b'private PDF export'
    assert not (prepared.folder/exported.name).exists()
    assert not (restored.folder/exported.name).exists()
    # Extra documents are tolerated, but declared executable files remain checked.
    (old/'Planificateur-SDG.exe').write_bytes(b'corrupted program')
    with pytest.raises(ValueError):prepare_update(package,repo,destination,current_root=old)
