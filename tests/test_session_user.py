from gardeplan import session_user


def test_greeting_uses_the_session_and_sanitizes_controls(monkeypatch):
    monkeypatch.setattr('sys.platform','win32')
    monkeypatch.setattr(session_user.os,'getlogin',lambda:'  Marie\nLaurence\x00  ')
    assert session_user.greeting()=='Bonjour Marie Laurence !'


def test_missing_session_has_a_readable_fallback(monkeypatch):
    monkeypatch.setattr('sys.platform','win32')
    def unavailable():raise OSError('Session non accessible')
    monkeypatch.setattr(session_user.os,'getlogin',unavailable)
    monkeypatch.setattr(session_user.getpass,'getuser',lambda:'camille')
    assert session_user.greeting()=='Bonjour camille !'
    monkeypatch.setattr(session_user.getpass,'getuser',unavailable)
    assert session_user.greeting()=='Bonjour, bienvenue'


def test_home_greeting_is_plain_text_and_does_not_interpret_the_name(qapp,monkeypatch):
    from PySide6.QtCore import Qt
    from gardeplan.ui.home import HomePage
    monkeypatch.setattr('gardeplan.ui.home.greeting',lambda:'Bonjour <b>Camille</b> !')
    home=HomePage()
    try:
        assert home.greeting.text()=='Bonjour <b>Camille</b> !'
        assert home.greeting.textFormat()==Qt.TextFormat.PlainText
    finally:home.deleteLater();qapp.processEvents()
