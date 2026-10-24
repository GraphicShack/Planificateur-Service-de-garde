import pytest

pytest.importorskip("PySide6")
from PySide6.QtWidgets import QMessageBox
from gardeplan.ui.localization import install_french_translations


def test_standard_confirmation_buttons_are_in_french(qapp):
    assert install_french_translations(qapp)
    dialog = QMessageBox()
    dialog.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
    labels = {button.text().replace("&", "").casefold() for button in dialog.buttons()}
    assert labels == {"oui", "non"}
    dialog.deleteLater()
