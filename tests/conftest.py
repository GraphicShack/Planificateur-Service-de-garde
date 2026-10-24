from copy import deepcopy
import pytest
from gardeplan.models import (
    Week, Educator, Group, GroupPeriod, Window, Shift, Settings,
)


@pytest.fixture
def valid_week():
    """One open pedagogical day, with continuous pupils and opening/closing cover."""
    availability = [Window(day=d, start=0, end=1440) for d in range(5)]
    educators = [
        Educator(id='e1', name='Marie Tremblay', seniority=1,
                 target_minutes=645, max_minutes=3000,
                 availability=deepcopy(availability), color='#407C69'),
        Educator(id='e2', name='Alex Roy', seniority=2,
                 target_minutes=645, max_minutes=3000,
                 availability=deepcopy(availability), color='#536DA2'),
    ]
    group = Group(id='g1', name='Groupe A', color='#407C69', ratio=20,
                  min_educators=2,
                  periods=[GroupPeriod(day=0, start=420, end=1050, students=30)])
    shifts = [Shift(id=f's{i+1}', educator_id=e.id, group_id='g1', day=0,
                    start=410, end=1055, buffer_before=10, buffer_after=5)
              for i, e in enumerate(educators)]
    return Week(monday='2026-10-26', educators=educators, groups=[group],
                shifts=shifts, settings=Settings(),
                day_names={0: 'Journée pédagogique — Halloween'})


@pytest.fixture(scope='session')
def qapp():
    import os
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    pytest.importorskip('PySide6')
    from PySide6.QtWidgets import QApplication
    application = QApplication.instance() or QApplication([])
    yield application
