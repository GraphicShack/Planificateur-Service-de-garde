"""Traduction des commandes Qt standard (Oui, Non, Annuler, etc.)."""
from PySide6.QtCore import QLibraryInfo, QLocale, QTranslator


def install_french_translations(application):
    QLocale.setDefault(QLocale(QLocale.Language.French, QLocale.Country.Canada))
    previous = getattr(application, "_french_translator", None)
    if previous is not None:
        application.removeTranslator(previous)
        previous.deleteLater()
    translator = QTranslator(application)
    directory = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    loaded = translator.load("qtbase_fr", directory)
    if loaded:
        application.installTranslator(translator)
    application._french_translator = translator
    return loaded
