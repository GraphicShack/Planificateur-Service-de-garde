from copy import deepcopy
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from gardeplan.daily import day_plan
from gardeplan.storage import Repository
from gardeplan.ui.faq import FaqPage,FAQ_ENTRIES
from gardeplan.ui.main_window import MainWindow


def dispose(widget,qapp):
    if isinstance(widget,MainWindow):widget.autosave.stop();widget.dirty=False
    widget.close();widget.deleteLater();qapp.processEvents()


def test_faq_search_matches_accents_and_answers_and_has_an_empty_state(qapp):
    page=FaqPage();page.resize(720,600);page.show();qapp.processEvents()
    try:
        assert len(page.entries)==len(FAQ_ENTRIES) and not page.empty.isVisible()
        page.search.setText('educatrices');qapp.processEvents()
        matches=[e for e in page.entries if not e.isHidden()]
        assert matches and all(e.button.isChecked() and e.answer.isVisible() for e in matches)
        page.search.setText('PDF');qapp.processEvents()
        assert any('exporter' in e.button.accessibleName() for e in page.entries if not e.isHidden())
        page.search.setText('Introuvable_987654');qapp.processEvents()
        assert page.empty.isVisible() and all(e.isHidden() for e in page.entries)
        page.search.clear();qapp.processEvents()
        assert not page.empty.isVisible() and all(not e.isHidden() and not e.answer.isVisible() for e in page.entries)
    finally:dispose(page,qapp)


def test_faq_question_is_keyboard_operable_and_wraps_on_small_screens(qapp):
    page=FaqPage();page.resize(480,550);page.show();qapp.processEvents()
    try:
        question=page.entries[0].button;question.setFocus()
        QTest.keyClick(question,Qt.Key.Key_Space);qapp.processEvents()
        assert question.isChecked() and page.entries[0].answer.isVisible()
        QTest.keyClick(question,Qt.Key.Key_Space)
        assert not question.isChecked()
        QTest.keyClick(question,Qt.Key.Key_F,Qt.KeyboardModifier.ControlModifier)
        assert page.search.hasFocus()
        assert page.horizontalScrollBar().maximum()==0
        assert all(entry.button.height()>=44 for entry in page.entries)
    finally:dispose(page,qapp)


def test_home_icons_open_visible_sections_and_ratio_is_shown(tmp_path,qapp):
    repo=Repository(tmp_path/'home.sqlite');window=MainWindow(repo,day_plan('2026-11-02'))
    window.show();qapp.processEvents()
    original=deepcopy(window.week.to_dict())
    try:
        assert window.content_stack.currentWidget() is window.home_page
        destinations=[(window.rail_buttons['users'],window.team_page),
                      (window.enrolment_button,window.enrolment_page),
                      (window.top_alert_button,window.alert_panel)]
        for button,target in destinations:
            assert button.isVisible() and button.isEnabled()
            QTest.mouseClick(button,Qt.MouseButton.LeftButton);qapp.processEvents()
            assert window.content_stack.currentWidget() is window.planner_page
            assert window.management_stack.currentWidget() is target and window.sidebar.isVisible()
            window.home_button.click();qapp.processEvents()
        QTest.mouseClick(window.coverage_toggle,Qt.MouseButton.LeftButton);qapp.processEvents()
        assert window.content_stack.currentWidget() is window.planner_page
        assert window.coverage_toggle.isChecked() and window.calendar.coverage_band.isVisible()
        window.home_button.click();QTest.mouseClick(window.faq_button,Qt.MouseButton.LeftButton);qapp.processEvents()
        assert window.content_stack.currentWidget() is window.faq_page and window.faq_page.search.hasFocus()
        assert window.week.to_dict()==original and repo.latest_week() is None
        assert window.faq_button.property('active') and not window.home_button.property('active')
        window.home_button.click();qapp.processEvents()
        assert window.content_stack.currentWidget() is window.home_page
    finally:dispose(window,qapp)


def test_f1_opens_faq_without_losing_unsaved_changes(tmp_path,qapp):
    window=MainWindow(Repository(tmp_path/'faq.sqlite'),day_plan('2026-11-02'),start_home=False)
    window.show();qapp.processEvents()
    window.week.day_names[0]='Modification en cours';window.dirty=True;window.autosave.stop()
    before=deepcopy(window.week.to_dict())
    try:
        QTest.keyClick(window,Qt.Key.Key_F1);qapp.processEvents()
        assert window.content_stack.currentWidget() is window.faq_page
        window.faq_page.search.setText('pauses');qapp.processEvents()
        assert window.week.to_dict()==before and window.dirty
        window.rail_buttons['calendar'].click();qapp.processEvents()
        assert window.week.to_dict()==before and window.dirty
    finally:dispose(window,qapp)


def test_all_sidebar_icons_remain_reachable_by_tab_on_a_short_window(tmp_path,qapp):
    window=MainWindow(Repository(tmp_path/'short.sqlite'),day_plan('2026-11-02'))
    window.resize(640,480);window.show()
    for _ in range(4):qapp.processEvents()
    try:
        buttons=[window.home_button,*window.rail_buttons.values(),window.enrolment_button,
                 window.coverage_toggle,window.top_alert_button,window.faq_button,window.folder_button,window.more_button]
        window.home_button.setFocus();qapp.processEvents()
        for index,button in enumerate(buttons):
            assert button.hasFocus(),f'Icône inaccessible au clavier : {index}'
            center=button.mapTo(window.navigation_scroll.viewport(),button.rect().center())
            assert window.navigation_scroll.viewport().rect().contains(center)
            assert window.navigation_scroll.viewport().rect().contains(button.mapTo(window.navigation_scroll.viewport(),button.rect().topLeft()))
            assert window.navigation_scroll.viewport().rect().contains(button.mapTo(window.navigation_scroll.viewport(),button.rect().bottomRight()))
            assert button.width()>=44 and button.height()>=44
            if index<len(buttons)-1:QTest.keyClick(button,Qt.Key.Key_Tab);qapp.processEvents()
        assert window.navigation_scroll.verticalScrollBar().maximum()>0
    finally:dispose(window,qapp)
