from copy import deepcopy
import pytest
from PySide6.QtCore import Qt,QTimer
from PySide6.QtGui import QImageReader
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from gardeplan.ui.faq import FaqPage,FAQ_ENTRIES
from gardeplan.ui.faq_media import CAPTURES,CAPTURE_ROOT,CaptureDialog,FaqFigure


def dispose(widget,qapp):
    widget.close();widget.deleteLater();qapp.processEvents()


def test_every_article_has_a_readable_local_capture(qapp):
    keys={key for _,_,_,captures in FAQ_ENTRIES for key in captures}
    assert keys==set(CAPTURES)
    for spec in CAPTURES.values():
        path=CAPTURE_ROOT/spec.filename
        assert path.is_file(),spec.filename
        reader=QImageReader(str(path))
        assert reader.canRead() and reader.size().isValid(),spec.filename
        assert not reader.read().isNull(),spec.filename
        assert spec.caption


def test_capture_previews_load_on_expansion_and_release_on_collapse(qapp):
    page=FaqPage();page.resize(760,700);page.show();qapp.processEvents()
    try:
        assert all(f.thumbnail.pixmap is None for entry in page.entries for f in entry.figures)
        first=page.entries[0];first.button.click();qapp.processEvents()
        assert first.figures and all(f.thumbnail.pixmap is not None and not f.thumbnail.pixmap.isNull() for f in first.figures)
        first.button.click();qapp.processEvents()
        assert all(f.thumbnail.pixmap is None for f in first.figures)
    finally:dispose(page,qapp)


def test_illustrated_answer_fits_a_small_faq_without_horizontal_scroll(qapp):
    page=FaqPage();page.resize(480,550);page.show();page.search.setText('imprimer')
    for _ in range(3):qapp.processEvents()
    try:
        shown=[entry for entry in page.entries if not entry.isHidden()]
        assert shown and any(entry.figures for entry in shown)
        assert page.horizontalScrollBar().maximum()==0
        assert all(f.thumbnail.width()<=page.viewport().width() for e in shown for f in e.figures)
    finally:dispose(page,qapp)


def test_capture_viewer_zoom_fit_resize_and_escape(qapp):
    dialog=CaptureDialog(CAPTURES['grille']);dialog.resize(640,480);dialog.show()
    for _ in range(3):qapp.processEvents()
    try:
        assert dialog.fit_mode and dialog.zoom<=1
        assert dialog.image.width()<=dialog.scroll.viewport().width()
        assert dialog.image.height()<=dialog.scroll.viewport().height()
        dialog.actual_button.click();qapp.processEvents()
        assert not dialog.fit_mode and dialog.zoom==1
        assert dialog.image.size()==dialog.original.size()
        dialog.resize(700,500);qapp.processEvents()
        assert dialog.zoom==1
        dialog.in_button.click();assert dialog.zoom==pytest.approx(1.25)
        dialog.out_button.click();assert dialog.zoom==pytest.approx(1)
        dialog.fit_button.click();qapp.processEvents()
        assert dialog.fit_mode and dialog.image.width()<=dialog.scroll.viewport().width()
        QTest.keyClick(dialog,Qt.Key.Key_Escape)
        assert not dialog.isVisible()
    finally:dispose(dialog,qapp)


def test_enter_opens_real_capture_dialog_without_changing_the_schedule(tmp_path,qapp):
    from gardeplan.daily import day_plan
    from gardeplan.storage import Repository
    from gardeplan.ui.main_window import MainWindow
    window=MainWindow(Repository(tmp_path/'faq.sqlite'),day_plan('2026-11-02'))
    window.show();window.show_faq();window.faq_page.entries[0].button.click();qapp.processEvents()
    original=deepcopy(window.week.to_dict());seen=[]
    timer=QTimer();timer.setSingleShot(True)
    def close_dialog():
        current=QApplication.activeModalWidget()
        seen.append(isinstance(current,CaptureDialog) and not current.original.isNull())
        if isinstance(current,CaptureDialog):QTest.keyClick(current,Qt.Key.Key_Escape)
    timer.timeout.connect(close_dialog)
    try:
        button=window.faq_page.entries[0].figures[0].open_button
        window.faq_page.ensureWidgetVisible(button);button.setFocus();qapp.processEvents()
        timer.start(30);QTest.keyClick(button,Qt.Key.Key_Return)
        assert seen==[True]
        assert window.week.to_dict()==original and not window.dirty
    finally:
        timer.stop();window.autosave.stop();dispose(window,qapp)


def test_missing_capture_keeps_help_usable_and_close_available(tmp_path,qapp,monkeypatch):
    monkeypatch.setattr('gardeplan.ui.faq_media.CAPTURE_ROOT',tmp_path)
    figure=FaqFigure(CAPTURES['accueil']);figure.show();qapp.processEvents()
    dialog=CaptureDialog(CAPTURES['accueil']);dialog.show();qapp.processEvents()
    try:
        assert not figure.open_button.isEnabled()
        assert figure.thumbnail.pixmap.isNull()
        assert 'indisponible' in dialog.image.text()
        assert not dialog.in_button.isEnabled() and dialog.close_button.isEnabled()
        dialog.close_button.click();assert not dialog.isVisible()
    finally:dispose(dialog,qapp);dispose(figure,qapp)
