"""Diagnostic du cœur sur un poste sans pytest/Qt6/OR-Tools.

Ce script exécute les fonctions de tests métier existantes. Un petit adaptateur
remplace seulement les décorateurs et pytest.raises : il n'implémente aucun
comportement applicatif. Les jeux de paramètres sont énumérés explicitement.
Il ne remplace pas ``python -m pytest -q`` avec les dépendances installées.
Exige ReportLab et pypdf pour vérifier réellement les documents PDF.
"""
from __future__ import annotations

from contextlib import contextmanager
import inspect
from pathlib import Path
import sys
import tempfile
import types
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests'))

# Adaptation locale à ce processus. Aucun module installé n'est modifié.
adapter = types.ModuleType('pytest')
adapter.fixture = lambda *args, **kwargs: (
    args[0] if args and callable(args[0]) else lambda function: function
)
adapter.mark = types.SimpleNamespace(
    parametrize=lambda *args, **kwargs: lambda function: function,
)


@contextmanager
def raises(expected, **kwargs):
    try:
        yield
    except expected as error:
        match = kwargs.get('match')
        if match:
            import re
            if not re.search(match, str(error)):
                raise AssertionError(f'Message attendu : {match!r}; reçu : {error!s}')
        return
    raise AssertionError(f'Exception attendue : {expected}')


adapter.raises = raises
# Une dépendance PDF manquante fait échouer ce diagnostic ; aucun faux succès.
adapter.importorskip = __import__
sys.modules['pytest'] = adapter

import conftest
import test_domain
import test_planning
import test_storage_pdf
import test_file_safety


class Patches:
    def __init__(self):
        self.items = []

    def setattr(self, *args):
        if isinstance(args[0], str):
            item = patch(args[0], args[1])
        else:
            item = patch.object(*args)
        item.start()
        self.items.append(item)

    def stop(self):
        for item in reversed(self.items):
            item.stop()


passed = failed = 0


def run_case(label, function, *args, **kwargs):
    global passed, failed
    try:
        function(*args, **kwargs)
        passed += 1
    except Exception as error:
        failed += 1
        print(f'ECHEC {label}: {error!r}')


for module in (test_domain, test_planning, test_storage_pdf, test_file_safety):
    for name, function in vars(module).items():
        if not name.startswith('test_'):
            continue
        parameters = inspect.signature(function).parameters
        if any(key not in ('valid_week', 'tmp_path', 'monkeypatch') for key in parameters):
            continue
        with tempfile.TemporaryDirectory(prefix='gardeplan-check-') as folder:
            patches = Patches()
            kwargs = {
                key: (conftest.valid_week() if key == 'valid_week'
                      else patches if key == 'monkeypatch' else Path(folder))
                for key in parameters
            }
            try:
                run_case(name, function, **kwargs)
            finally:
                patches.stop()

for value in (420.5, True, '07:00'):
    run_case('minute non entière', test_domain.test_non_integer_minutes_rejected_on_import,
             conftest.valid_week(), value)
for value in (True, '1.0', float('nan'), float('inf'), 0, 10):
    run_case('zoom invalide', test_domain.test_invalid_zoom_rejected_without_accepting_malformed_backup,
             conftest.valid_week(), value)
for names in ({True: 'Mardi'}, {1.5: 'Mardi'}, {'01': 'Mardi'}, {1: 'Mardi', '1': 'Doublon'}):
    run_case('clés de journée invalides', test_domain.test_invalid_or_duplicated_day_name_keys_rejected,
             conftest.valid_week(), names)
for args in ((-1, 20, 20), (5, 20, 20), (True, 20, 20),
             (0, -1, 20), (0, 20.5, 20), (0, True, 20),
             (0, 20, 0), (0, 20, -2), (0, 20, 20.5)):
    run_case('inscriptions invalides', test_planning.test_invalid_inputs_rejected,
             conftest.valid_week(), *args)

print(f'{passed} contrôles cœur réussis, {failed} échecs (Qt6/OR-Tools non exécutés)')
raise SystemExit(1 if failed else 0)
