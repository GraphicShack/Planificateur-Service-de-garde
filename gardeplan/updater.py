"""Prepare a separate portable version and a verified pre-update data snapshot.

The running executable is never overwritten. All preparation is transactional
inside a temporary folder, on the chosen destination volume. Existing versions
and their databases remain available if preparation or launch fails.
"""
from dataclasses import dataclass
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import shutil
import sqlite3
import tempfile
from uuid import uuid4

from .portable_package import (MANIFEST,extract_package,read_manifest,sha256,
                               validate_manifest,verify_folder)
from .storage import Repository

RECEIPT='mise-a-jour.json'
SNAPSHOT='retour-avant-maj'


@dataclass(frozen=True)
class PreparedUpdate:
    folder: Path
    executable: Path
    version: str
    platform: str
    operation: str='update'


def atomic_json(path,value):
    temporary=None
    try:
        with tempfile.NamedTemporaryFile('w',encoding='utf-8',dir=path.parent,prefix='.sdg-',delete=False) as handle:
            temporary=Path(handle.name);json.dump(value,handle,ensure_ascii=False,indent=2)
            handle.flush();os.fsync(handle.fileno())
        os.replace(temporary,path)
    finally:
        if temporary is not None:temporary.unlink(missing_ok=True)


def atomic_copy(source,destination):
    destination.parent.mkdir(parents=True,exist_ok=True)
    temporary=None
    try:
        with tempfile.NamedTemporaryFile('wb',dir=destination.parent,prefix='.sdg-',delete=False) as handle:
            temporary=Path(handle.name)
            with Path(source).open('rb') as input_file:shutil.copyfileobj(input_file,handle)
            handle.flush();os.fsync(handle.fileno())
        os.replace(temporary,destination)
    finally:
        if temporary is not None:temporary.unlink(missing_ok=True)


def _regular_tree(path):
    if path.is_symlink() or getattr(path,'is_junction',lambda:False)():raise ValueError('Un dossier de sauvegarde contient un lien. Conservez-le séparément avant la mise à jour.')
    for item in path.rglob('*'):
        if item.is_symlink() or getattr(item,'is_junction',lambda:False)() or not (item.is_dir() or item.is_file()):
            raise ValueError('Un dossier de sauvegarde contient un lien ou un fichier spécial non pris en charge.')


def _copy_preferences(data_folder,root):
    source=data_folder/'interface.json'
    if source.is_symlink():raise ValueError('Le fichier de préférences est un lien. La copie automatique est interrompue.')
    if source.is_file():
        atomic_copy(source,root/'donnees/interface.json')
        atomic_copy(source,root/SNAPSHOT/'interface.json')


def _snapshot(repository,root):
    for name in ('donnees',SNAPSHOT):
        path=root/name
        if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
            raise ValueError('Le dossier préparé contient un lien de données non autorisé.')
    snapshot=root/SNAPSHOT/'gardeplan.sqlite'
    repository.backup(snapshot)
    atomic_copy(snapshot,root/'donnees/gardeplan.sqlite')
    _copy_preferences(repository.path.parent,root)
    return sha256(snapshot)


def _destination(parent,version,operation='update'):
    name='Planificateur-SDG-'+version+('-retour' if operation=='rollback' else '')
    destination=parent/name
    if destination.exists():destination=parent/(name+'-'+uuid4().hex[:8])
    return destination


def _parent(parent,current_root):
    parent=Path(parent).expanduser().resolve()
    if not parent.is_dir():raise ValueError('Choisissez un dossier de destination existant.')
    if current_root is not None and parent.is_relative_to(current_root):
        raise ValueError('Choisissez un dossier extérieur au logiciel actuel, par exemple son dossier parent.')
    return parent


def prepare_update(package,repository,parent,*,current_root=None,current_version=None):
    current_root=Path(current_root).resolve() if current_root is not None else None
    parent=_parent(parent,current_root)
    previous=None
    if current_root is not None:
        if (current_root/MANIFEST).is_file():
            previous=verify_folder(current_root)
            if current_version is not None and previous['version']!=current_version:
                raise ValueError('La version du dossier actuel ne correspond pas au logiciel lancé.')
    destination=_destination(parent,package.manifest['version'])
    with tempfile.TemporaryDirectory(prefix='.sdg-mise-a-jour-',dir=parent) as temporary:
        root=extract_package(package,Path(temporary)/'nouvelle-version')
        # Copy only the application's known data. The active database is cloned
        # through SQLite, including every day and version, never copied live.
        backup_hash=_snapshot(repository,root)
        for name in ('backups','sauvegardes'):
            source=repository.path.parent/name
            if source.exists():
                _regular_tree(source)
                if parent.is_relative_to(source.resolve()):raise ValueError('La destination ne peut pas se trouver dans les sauvegardes à copier.')
                shutil.copytree(source,root/'donnees'/name)
        receipt={'schema':1,'operation':'update','version':package.manifest['version'],
                 'prepared_at':datetime.now(timezone.utc).isoformat(),
                 'previous_root':str(current_root) if previous is not None else None,
                 'previous_name':current_root.name if previous is not None and current_root.parent==parent else None,
                 'previous_version':previous['version'] if previous is not None else current_version,
                 'source_database':str(repository.path),'pending':True,
                 'source_database_relative':repository.path.relative_to(current_root).as_posix() if current_root is not None and repository.path.is_relative_to(current_root) else None,
                 'snapshot_sha256':backup_hash}
        atomic_json(root/RECEIPT,receipt)
        if destination.exists():raise ValueError('Le dossier de destination vient d’être créé par une autre opération. Recommencez.')
        root.rename(destination)
    return PreparedUpdate(destination,destination/package.manifest['executable'],package.manifest['version'],package.manifest['platform'])


def read_receipt(root):
    root=Path(root).resolve();path=root/RECEIPT
    if path.is_symlink() or path.stat().st_size>65536:raise ValueError('L’historique de mise à jour est invalide.')
    data=json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(data,dict) or data.get('schema')!=1 or data.get('operation') not in ('update','rollback'):
        raise ValueError('L’historique de mise à jour est invalide.')
    return data


def refresh_prepared(prepared,repository):
    """Refresh the prepared copy just before launch, after the final save."""
    if prepared.operation!='update':return
    root=prepared.folder
    receipt=read_receipt(root)
    from PySide6.QtCore import QLockFile
    lock=QLockFile(str(root/'donnees/gardeplan.sqlite')+'.lock')
    if not lock.tryLock(100):raise ValueError('La nouvelle version utilise déjà ses données. Fermez-la avant de terminer cette mise à jour.')
    try:
        receipt['snapshot_sha256']=_snapshot(repository,root)
        receipt['prepared_at']=datetime.now(timezone.utc).isoformat()
        atomic_json(root/RECEIPT,receipt)
    finally:lock.unlock()


def previous_root(root,receipt):
    name=receipt.get('previous_name')
    if isinstance(name,str) and name not in ('','.','..') and not any(c in name for c in '/\\:'):
        sibling=root.parent/name
        if sibling.is_dir():return sibling.resolve()
    value=receipt.get('previous_root')
    if not isinstance(value,str) or not value:raise ValueError('Aucune version précédente conservée par cet assistant n’est disponible.')
    return Path(value).resolve()


class ReadOnlySource:
    """Clone committed source data without migrating or changing the old file."""
    def __init__(self,path):self.path=path

    def backup(self,destination):
        destination.parent.mkdir(parents=True,exist_ok=True)
        temporary=None
        try:
            fd,name=tempfile.mkstemp(dir=destination.parent,prefix='.sdg-source-',suffix='.sqlite')
            os.close(fd);temporary=Path(name)
            source=sqlite3.connect(self.path.as_uri()+'?mode=ro',uri=True)
            target=sqlite3.connect(temporary)
            try:
                source.backup(target)
                if target.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('La base d’origine ne passe pas la vérification d’intégrité.')
            finally:target.close();source.close()
            os.replace(temporary,destination)
        finally:
            if temporary is not None:temporary.unlink(missing_ok=True)


def activate_pending(root):
    """On first launch, get the last saved source data after the old app closes."""
    root=Path(root).resolve()
    if not (root/RECEIPT).exists():return
    receipt=read_receipt(root)
    if receipt.get('operation')!='update' or receipt.get('pending') is not True:return
    source_path=receipt.get('source_database')
    if receipt.get('previous_root'):
        previous=previous_root(root,receipt)
        manifest=read_manifest(previous)
        if manifest['version']!=receipt.get('previous_version'):
            raise ValueError('Le dossier de départ a changé. Repréparez la mise à jour depuis la version actuelle.')
        relative_path=receipt.get('source_database_relative')
        if isinstance(relative_path,str):
            from .portable_package import relative
            source_path=previous/relative(relative_path)
            if not source_path.resolve().is_relative_to(previous):raise ValueError('Le chemin de la base d’origine est invalide.')
    if not source_path or not Path(source_path).is_file():raise ValueError('La base d’origine est introuvable. Conservez les deux dossiers et leur sauvegarde.')
    source_path=Path(source_path).resolve()
    if source_path==(root/'donnees/gardeplan.sqlite').resolve():raise ValueError('La base d’origine ne peut pas être la nouvelle copie.')
    from PySide6.QtCore import QLockFile
    source_lock=QLockFile(str(source_path)+'.lock');source_lock.setStaleLockTime(30000)
    if not source_lock.tryLock(3000):raise ValueError('Fermez l’ancienne version avant d’ouvrir celle-ci. Vos données restent conservées.')
    target_lock=QLockFile(str(root/'donnees/gardeplan.sqlite')+'.lock')
    try:
        if not target_lock.tryLock(100):raise ValueError('La nouvelle version utilise déjà ses données.')
        try:
            receipt=read_receipt(root)
            if receipt.get('pending') is not True:return
            receipt['snapshot_sha256']=_snapshot(ReadOnlySource(source_path),root)
            receipt['pending']=False;receipt['activated_at']=datetime.now(timezone.utc).isoformat()
            atomic_json(root/RECEIPT,receipt)
        finally:target_lock.unlock()
    finally:source_lock.unlock()


def prepare_rollback(current_root,repository,parent):
    current_root=Path(current_root).resolve()
    receipt=read_receipt(current_root)
    if receipt.get('operation')!='update' or not receipt.get('previous_root'):
        raise ValueError('Aucune version précédente conservée par cet assistant n’est disponible.')
    previous=previous_root(current_root,receipt)
    data=verify_folder(previous)
    current=read_manifest(current_root)
    if (data['version']!=receipt.get('previous_version') or data['platform']!=current['platform']
            or data['architecture']!=current['architecture']):
        raise ValueError('Le dossier de la version précédente a changé ou n’est plus compatible.')
    snapshot=current_root/SNAPSHOT/'gardeplan.sqlite'
    if snapshot.is_symlink() or not snapshot.resolve().is_relative_to(current_root) or sha256(snapshot)!=receipt.get('snapshot_sha256'):
        raise ValueError('La sauvegarde d’avant mise à jour est manquante ou modifiée.')
    parent=_parent(parent,current_root)
    if parent.is_relative_to(previous):raise ValueError('Choisissez un dossier extérieur à la version précédente.')
    destination=_destination(parent,data['version'],'rollback')
    with tempfile.TemporaryDirectory(prefix='.sdg-retour-',dir=parent) as temporary:
        root=Path(temporary)/'version-restauree';root.mkdir()
        for name in data['directories']:(root/name).mkdir(parents=True,exist_ok=True)
        for name in [MANIFEST,*data['files']]:
            (root/name).parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(previous/name,root/name)
        for name,target in data['links'].items():os.symlink(target,root/name)
        verify_folder(root,data)
        atomic_copy(snapshot,root/'donnees/gardeplan.sqlite')
        preferences=current_root/SNAPSHOT/'interface.json'
        if preferences.is_symlink():raise ValueError('La sauvegarde des préférences est un lien non autorisé.')
        if preferences.is_file():atomic_copy(preferences,root/'donnees/interface.json')
        # Also retain the current data, independently of the restored old copy.
        repository.backup(root/'donnees/sauvegardes/avant-retour.sqlite')
        atomic_json(root/RECEIPT,{'schema':1,'operation':'rollback','version':data['version'],
                                'previous_root':None,'restored_from':str(current_root),
                                'prepared_at':datetime.now(timezone.utc).isoformat()})
        if destination.exists():raise ValueError('Le dossier de retour existe déjà. Recommencez.')
        root.rename(destination)
    return PreparedUpdate(destination,destination/data['executable'],data['version'],data['platform'],'rollback')
