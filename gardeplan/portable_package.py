"""Local portable package format: inventory, hashes and safe ZIP extraction."""
from dataclasses import dataclass
import argparse
import hashlib
import json
import os
from pathlib import Path,PurePosixPath
import platform
import posixpath
import re
import stat
import sys
import unicodedata
import zipfile

MANIFEST='version-portable.json'
APP_ID='ca.planificateur.sdg'
ROOT_NAME='Planificateur-SDG'
EXECUTABLES={'windows':'Planificateur-SDG.exe','macos':'Planificateur-SDG.app/Contents/MacOS/Planificateur-SDG'}
MAX_SIZE=4*1024**3


def sha256(path):
    with Path(path).open('rb') as handle:return hashlib.file_digest(handle,'sha256').hexdigest()


def version(value):
    if not isinstance(value,str) or not re.fullmatch(r'\d+\.\d+\.\d+',value):
        raise ValueError('La version de l’archive est invalide.')
    return tuple(int(x) for x in value.split('.'))


def machine():
    name=platform.machine().casefold()
    if name in ('amd64','x86_64','x64'):return 'x64'
    if name in ('arm64','aarch64'):return 'arm64'
    return name


def system():
    if sys.platform=='win32':return 'windows'
    if sys.platform=='darwin':return 'macos'
    raise ValueError('L’assistant utilise les versions portables Windows ou macOS du logiciel.')


def relative(value):
    if (not isinstance(value,str) or not value or '\\' in value or ':' in value or '\x00' in value
            or PurePosixPath(value).is_absolute() or any(p in ('','..','.') for p in value.split('/'))):
        raise ValueError('L’archive contient un chemin de fichier non autorisé.')
    for part in value.split('/'):
        if part.endswith((' ','.')) or part.split('.')[0].upper() in {'CON','PRN','AUX','NUL',*(f'COM{i}' for i in range(1,10)),*(f'LPT{i}' for i in range(1,10))}:
            raise ValueError('L’archive contient un nom de fichier incompatible.')
    return value


def inventory(root):
    files={};links={};directories=[]
    for item in sorted(Path(root).rglob('*')):
        name=item.relative_to(root).as_posix()
        if name==MANIFEST or name.split('/')[0]=='donnees':continue
        relative(name)
        if getattr(item,'is_junction',lambda:False)():raise ValueError('Le logiciel contient une jonction de dossiers non prise en charge.')
        if item.is_symlink():links[name]=os.readlink(item)
        elif item.is_dir():directories.append(name)
        elif item.is_file():files[name]=sha256(item)
        else:raise ValueError('Le dossier portable contient un fichier spécial non pris en charge.')
    return files,links,directories


def _resolve_link(path,links,depth=0,seen=()):
    if depth>64 or path in seen:raise ValueError('Un lien de l’archive est circulaire.')
    parts=path.split('/')
    for i in range(len(parts)):
        prefix='/'.join(parts[:i+1])
        if prefix not in links:continue
        target=links[prefix]
        if not isinstance(target,str) or not target or target.startswith('/') or '\\' in target or ':' in target:
            raise ValueError('Un lien de l’archive sort du logiciel.')
        value=posixpath.normpath(posixpath.join(posixpath.dirname(prefix),target,*parts[i+1:]))
        relative(value)
        if value.split('/')[0]=='donnees':raise ValueError('Un lien du logiciel ne peut pas cibler les données.')
        return _resolve_link(value,links,depth+1,seen+(path,))
    return path


def validate_manifest(data,expected_platform=None,expected_arch=None):
    if not isinstance(data,dict) or data.get('schema')!=1 or data.get('application')!=APP_ID:
        raise ValueError('Ce ZIP n’est pas une mise à jour portable compatible du Planificateur.')
    version(data.get('version'))
    target=data.get('platform');arch=data.get('architecture')
    if target not in EXECUTABLES or data.get('executable')!=EXECUTABLES[target] or arch not in ('x64','arm64'):
        raise ValueError('Le type de logiciel contenu dans le ZIP est invalide.')
    if expected_platform and target!=expected_platform:raise ValueError('Ce ZIP ne correspond pas au système de cet ordinateur.')
    if expected_arch and arch!=expected_arch:raise ValueError('Ce ZIP ne correspond pas à l’architecture de cet ordinateur.')
    files=data.get('files');links=data.get('links');directories=data.get('directories')
    if not isinstance(files,dict) or not isinstance(links,dict) or not isinstance(directories,list):
        raise ValueError('L’inventaire de l’archive est incomplet.')
    names=list(files)+list(links)+directories
    if len(names)>100000 or any(not isinstance(n,str) for n in names):raise ValueError('L’inventaire de l’archive est invalide.')
    folded=[unicodedata.normalize('NFC',relative(n)).casefold() for n in names]
    if len(set(folded))!=len(names):raise ValueError('L’archive contient des chemins ambigus ou répétés.')
    if MANIFEST in names or 'mise-a-jour.json' in names or any(n.split('/')[0] in ('donnees','retour-avant-maj') for n in names):
        raise ValueError('La mise à jour ne doit pas contenir de données personnelles.')
    if not {'portable.mode',data['executable']}<=files.keys():raise ValueError('Le logiciel portable est incomplet.')
    for digest in files.values():
        if not isinstance(digest,str) or not re.fullmatch('[0-9a-f]{64}',digest):raise ValueError('Une empreinte de fichier est invalide.')
    known=set(names)
    for name in names:
        if any(str(parent) not in directories for parent in PurePosixPath(name).parents if str(parent)!='.'):
            raise ValueError('L’archive contient un fichier sous un lien ou un dossier non déclaré.')
    for name in links:
        if _resolve_link(name,links) not in known:raise ValueError('Un lien du logiciel est introuvable.')
    if target=='windows' and links:raise ValueError('Une archive Windows ne doit pas nécessiter la création de liens système.')
    if 'minimum_macos' in data and (not isinstance(data['minimum_macos'],str) or not re.fullmatch(r'\d+\.\d+(?:\.\d+)?',data['minimum_macos'])):
        raise ValueError('La version minimale de macOS est invalide.')
    return data


def write_manifest(root,release_version,target=None,architecture=None):
    root=Path(root)
    files,links,directories=inventory(root)
    target=target or system()
    data={'schema':1,'application':APP_ID,'version':release_version,'platform':target,
          'architecture':architecture or machine(),'executable':EXECUTABLES[target],
          'files':files,'links':links,'directories':directories}
    if target=='macos' and platform.mac_ver()[0]:data['minimum_macos']=platform.mac_ver()[0].split('.')[0]+'.0'
    validate_manifest(data)
    (root/MANIFEST).write_text(json.dumps(data,ensure_ascii=False,sort_keys=True),encoding='utf-8')
    return data


def read_manifest(root):
    path=Path(root)/MANIFEST
    if path.is_symlink() or path.stat().st_size>8*1024**2:raise ValueError('Le manifeste portable est invalide.')
    return validate_manifest(json.loads(path.read_text(encoding='utf-8')))


def verify_folder(root,data=None):
    root=Path(root);data=validate_manifest(data or read_manifest(root))
    files,links,directories=inventory(root)
    # Receipts and pre-update snapshots belong to the update workflow, not the executable.
    files={k:v for k,v in files.items() if k!='mise-a-jour.json' and not k.startswith('retour-avant-maj/')}
    directories=[d for d in directories if d!='retour-avant-maj' and not d.startswith('retour-avant-maj/')]
    if files!=data['files'] or links!=data['links'] or set(directories)!=set(data['directories']):
        raise ValueError('Des fichiers du logiciel sont manquants, modifiés ou non prévus dans l’inventaire.')
    return data


def create_archive(root,destination):
    root=Path(root);data=verify_folder(root)
    if (root/'donnees').exists() and any((root/'donnees').iterdir()):
        raise ValueError('Le dossier de fabrication contient des données. Elles ne doivent pas être distribuées.')
    destination=Path(destination)
    with zipfile.ZipFile(destination,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6,allowZip64=True) as archive:
        for directory in ['',*data['directories'],'donnees']:
            info=zipfile.ZipInfo(ROOT_NAME+('/'+directory if directory else '')+'/')
            info.create_system=3;info.external_attr=(stat.S_IFDIR|0o755)<<16
            archive.writestr(info,b'')
        for name in [MANIFEST,*data['files']]:archive.write(root/name,ROOT_NAME+'/'+name)
        for name,target in data['links'].items():
            info=zipfile.ZipInfo(ROOT_NAME+'/'+name);info.create_system=3
            info.external_attr=(stat.S_IFLNK|0o777)<<16
            archive.writestr(info,target.encode('utf-8'))
    return destination


@dataclass(frozen=True)
class Package:
    path: Path
    digest: str
    manifest: dict


def inspect_archive(path,current_version,expected_platform=None,expected_arch=None,*,allow_same=False):
    path=Path(path).resolve()
    with zipfile.ZipFile(path) as archive:
        infos=archive.infolist()
        if len(infos)>100000 or sum(i.file_size for i in infos)>MAX_SIZE:raise ValueError('Le ZIP dépasse la taille autorisée pour un logiciel portable.')
        names={};folded=set()
        for info in infos:
            name=relative(info.filename.rstrip('/'))
            key=unicodedata.normalize('NFC',name).casefold()
            if key in folded:raise ValueError('Le ZIP contient des entrées répétées ou ambiguës.')
            folded.add(key);names[name]=info
            if info.flag_bits&1:raise ValueError('Les ZIP protégés par mot de passe ne sont pas pris en charge.')
        manifest_info=names.get(ROOT_NAME+'/'+MANIFEST)
        if manifest_info is None or manifest_info.file_size>8*1024**2:
            raise ValueError('Ce ZIP ne possède pas le manifeste de mise à jour. Utilisez un ZIP portable publié à partir de la version 0.5.0.')
        data=validate_manifest(json.loads(archive.read(manifest_info)),expected_platform or system(),expected_arch or machine())
        if version(data['version'])<version(current_version) or (not allow_same and version(data['version'])==version(current_version)):
            raise ValueError('Choisissez une version plus récente que celle actuellement utilisée.')
        if data['platform']=='macos' and sys.platform=='darwin' and data.get('minimum_macos'):
            required=tuple(int(x) for x in data['minimum_macos'].split('.'))
            actual=tuple(int(x) for x in platform.mac_ver()[0].split('.'))
            if actual<required:raise ValueError('Cette version nécessite macOS '+data['minimum_macos']+' ou plus récent.')
        expected={ROOT_NAME,ROOT_NAME+'/'+MANIFEST,ROOT_NAME+'/donnees'}
        expected.update(ROOT_NAME+'/'+n for n in [*data['files'],*data['links'],*data['directories']])
        if set(names)!=expected:raise ValueError('Le ZIP contient des fichiers inattendus ou incomplets.')
        for name,info in names.items():
            kind=stat.S_IFMT(info.external_attr>>16)
            relative_name=name[len(ROOT_NAME)+1:]
            if relative_name in data['links']:
                if kind!=stat.S_IFLNK or archive.read(info).decode('utf-8')!=data['links'][relative_name]:
                    raise ValueError('Un lien du ZIP ne correspond pas à son inventaire.')
            elif name in {ROOT_NAME,ROOT_NAME+'/donnees'} or relative_name in data['directories']:
                if not info.is_dir():raise ValueError('Un dossier du ZIP est invalide.')
            elif kind not in (0,stat.S_IFREG):raise ValueError('Le ZIP contient un fichier spécial non autorisé.')
    return Package(path,sha256(path),data)


def extract_package(package,destination):
    if sha256(package.path)!=package.digest:raise ValueError('Le ZIP a changé depuis son analyse. Sélectionnez-le à nouveau.')
    root=Path(destination);root.mkdir(parents=True,exist_ok=False)
    data=validate_manifest(package.manifest)
    for name in data['directories']:(root/name).mkdir(parents=True,exist_ok=True)
    (root/'donnees').mkdir(exist_ok=True)
    with zipfile.ZipFile(package.path) as archive:
        for name in [MANIFEST,*data['files']]:
            target=root/name;info=archive.getinfo(ROOT_NAME+'/'+name)
            target.parent.mkdir(parents=True,exist_ok=True)
            with archive.open(info) as source,target.open('xb') as output:
                import shutil
                shutil.copyfileobj(source,output)
            if name in data['files'] and sha256(target)!=data['files'][name]:raise ValueError('L’empreinte d’un fichier ne correspond pas : '+name)
            mode=(info.external_attr>>16)&0o777
            target.chmod(mode or 0o644)
        for name,target in data['links'].items():os.symlink(target,root/name)
    if read_manifest(root)!=data:raise ValueError('Le manifeste du ZIP a changé pendant son extraction.')
    verify_folder(root,data)
    return root


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('operation',choices=['manifest','archive'])
    parser.add_argument('root',type=Path);parser.add_argument('value')
    args=parser.parse_args()
    write_manifest(args.root,args.value) if args.operation=='manifest' else create_archive(args.root,args.value)
