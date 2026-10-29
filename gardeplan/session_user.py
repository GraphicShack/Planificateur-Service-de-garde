"""Read the local session identity, without an account or a network service."""
import getpass
import os
import unicodedata


def _clean(value):
    if not isinstance(value,str):return ''
    value=unicodedata.normalize('NFC',value)
    return ' '.join(''.join(c if c.isprintable() else ' ' for c in value).split())[:80]


def session_name():
    try:
        # macOS keeps the friendly local account name in the passwd record.
        import sys
        if sys.platform=='darwin':
            import pwd
            account=pwd.getpwuid(os.getuid())
            name=_clean(account.pw_gecos.split(',')[0]) or _clean(account.pw_name)
            if name:return name
    except (ImportError,OSError,KeyError,AttributeError):
        pass
    for lookup in (os.getlogin,getpass.getuser):
        try:
            name=_clean(lookup())
            if name:return name
        except (OSError,KeyError,ImportError):
            pass
    return ''


def greeting():
    name=session_name()
    return f'Bonjour {name} !' if name else 'Bonjour, bienvenue'
