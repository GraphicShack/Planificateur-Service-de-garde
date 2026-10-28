"""Contrôle réel de la distribution, exécuté par la compilation Windows.

Les données d'essai demeurent dans un dossier temporaire. Le contrôle n'ouvre
jamais la base personnelle et ne présente aucune boîte de dialogue.
"""
from __future__ import annotations

from datetime import date, timedelta
from contextlib import ExitStack
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
from unittest.mock import patch

from gardeplan import __version__
from gardeplan.data_paths import portable_root, DATA_FOLDER


def check_installation(destination: str | Path) -> int:
    """Écrit un compte rendu JSON ; retourne zéro uniquement si tout réussit."""
    report = {
        "success": False,
        "version": __version__,
        "frozen": bool(getattr(sys, "frozen", False)),
        "checks": {},
    }
    root = portable_root()
    report["portable_mode"] = root is not None
    application = window = document = view = None

    def release_gui():
        nonlocal window, document, view
        if view is not None:
            view.setDocument(None)
            view.close()
            view = None
        if document is not None:
            document.close()
            document = None
        if window is not None:
            window.autosave.stop()
            window.hide()
            window.deleteLater()
            window = None
        if application is not None:
            application.processEvents()

    try:
        from PySide6.QtCore import qVersion, QSize, QDate
        from PySide6.QtWidgets import QApplication
        from PySide6.QtPdf import QPdfDocument
        from PySide6.QtPdfWidgets import QPdfView
        from PySide6.QtPrintSupport import QPrinter
        from PySide6.QtSvg import QSvgRenderer

        from gardeplan.models import Week, Educator, Group, GroupPeriod, Shift
        from gardeplan.optimizer import generate
        from gardeplan.pdf import export_general, export_individual
        from gardeplan.storage import Repository
        from gardeplan.validation import validate
        from gardeplan.ui.main_window import MainWindow
        from gardeplan.ui.visuals import LOGO_PATH
        from gardeplan.ui.localization import install_french_translations

        report["qt_version"] = qVersion()
        application = QApplication.instance() or QApplication(["GardePlan-verification"])
        report["qt_platform"] = application.platformName()
        if not install_french_translations(application):
            raise RuntimeError("La traduction française des commandes Qt n'est pas disponible.")
        if not LOGO_PATH.is_file() or not QSvgRenderer(str(LOGO_PATH)).isValid():
            raise RuntimeError("Le logo vectoriel n'est pas disponible dans la distribution.")
        report["checks"]["qt_application"] = True

        def refuse_network(*args, **kwargs):
            raise RuntimeError("Le contrôle hors ligne a détecté une tentative de connexion.")

        # Le logiciel est livré sans service réseau. Tester les opérations avec
        # les sockets interdites confirme aussi le comportement du paquet gelé.
        with patch.object(socket, "socket", refuse_network), patch.object(socket, "create_connection", refuse_network):
            with ExitStack() as cleanup:
                data_folder = root / DATA_FOLDER if root is not None else None
                if data_folder is not None:
                    data_folder.mkdir(parents=True, exist_ok=True)
                directory = cleanup.enter_context(tempfile.TemporaryDirectory(
                    prefix="gardeplan-verification-", dir=data_folder))
                # Fermer les PDF avant la suppression du dossier, y compris en
                # cas d'échec : Windows refuse de supprimer un fichier ouvert.
                cleanup.callback(release_gui)
                folder = Path(directory)
                today = date.today()
                monday = (today - timedelta(days=today.weekday())).isoformat()
                from gardeplan.daily import day_plan
                week = day_plan(monday)
                week.educators = [Educator(f"e{i+1}", f"Éducatrice test {i+1}", seniority=i+1,
                                           target_minutes=0, max_minutes=480) for i in range(4)]
                week.groups = [Group(f"g{i+1}", f"Groupe test {i+1}",
                                     periods=[GroupPeriod(0,420,1050,20)]) for i in range(2)]
                week.shifts = [Shift(f"s{i+1}", f"e{i+1}", f"g{i%2+1}",0,
                                     410 if i<2 else 720,735 if i<2 else 1055,
                                     10 if i<2 else 15,0 if i<2 else 5) for i in range(4)]
                week.day_names = {0: "Journée pédagogique — Vérification"}
                if any(issue.severity == "error" for issue in validate(week)):
                    raise RuntimeError("Le jeu de contrôle métier n'est pas valide.")
                report["checks"]["coverage_and_exact_minutes"] = True
                repository = Repository(folder / "verification.sqlite")
                repository.save(week)
                restored = repository.load_day(week.planning_date)
                if restored is None or restored.to_dict() != week.to_dict():
                    raise RuntimeError("La sauvegarde SQLite ne se rouvre pas à l'identique.")
                repository.backup(folder / "copie.sqlite")
                report["checks"]["sqlite_save_reopen_backup"] = True
                if root is not None:
                    report["checks"]["portable_data_write"] = folder.parent == data_folder

                window = MainWindow(repository, restored)
                window.show()
                application.processEvents()
                if window.content_stack.currentWidget() is not window.home_page or window.home_page.grab().isNull():
                    raise RuntimeError("La page d’accueil ne peut pas être dessinée.")
                report["checks"]["home_dashboard"] = True
                window.show_planner()
                window.set_mode("Jour")
                window.fit_day()
                application.processEvents()
                if window.calendar.canvas.grab().isNull():
                    raise RuntimeError("Le calendrier ne peut pas être dessiné.")
                report["checks"]["dashboard_day"] = True
                picker = window.week_date
                if picker.grab().isNull() or picker.height() < 44 or picker.font().pixelSize() < 16 or picker.calendarPopup():
                    raise RuntimeError("Le sélecteur de journée ne respecte pas les dimensions lisibles.")
                report["checks"]["readable_date_selector"] = True

                general_pdf = folder / "general.pdf"
                export_general(restored, general_pdf)
                individual_pdf = folder / "individuel.pdf"
                export_individual(restored, "e1", individual_pdf)
                for path in (general_pdf, individual_pdf):
                    if not path.read_bytes().startswith(b"%PDF-"):
                        raise RuntimeError("Le fichier exporté n'est pas un PDF.")
                document = QPdfDocument()
                document.load(str(general_pdf))
                if document.pageCount() < 1:
                    raise RuntimeError("Qt ne peut pas ouvrir le PDF exporté.")
                if document.render(0, QSize(900, 650)).isNull():
                    raise RuntimeError("Qt ne peut pas afficher le PDF exporté.")
                view = QPdfView()
                view.setDocument(document)
                printer = QPrinter(QPrinter.PrinterMode.HighResolution)
                printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
                # Vérifie la présence des modules d'impression, sans imprimante
                # physique ni boîte de dialogue sur le poste de compilation.
                report["checks"]["pdf_export_preview_print_modules"] = True

                request = Week.from_dict(restored.to_dict())
                request.shifts = []
                generated = generate(request, time_limit=15)
                if not generated.success or generated.proposal is None:
                    raise RuntimeError(f"La génération CP-SAT a échoué : {generated.message}")
                if any(issue.severity == "error" for issue in validate(generated.proposal)):
                    raise RuntimeError("Le solveur a renvoyé une proposition invalide.")
                from gardeplan.models import totals
                from gardeplan.coverage import coverage_timeline
                if {s.group_id for s in generated.proposal.shifts}!={g.id for g in request.groups}:
                    raise RuntimeError("Tous les groupes ne sont pas couverts par la génération.")
                if not all(0<totals(generated.proposal).get(e.id,0)<=480 for e in request.educators):
                    raise RuntimeError("La répartition de l’équipe ou le plafond de huit heures n’est pas respecté.")
                qualities=[]
                for person in request.educators:
                    shifts=[s for s in generated.proposal.shifts if s.educator_id==person.id]
                    qualities.append((-len(shifts),totals(generated.proposal)[person.id],-max(s.end for s in shifts)))
                if qualities!=sorted(qualities,reverse=True):
                    raise RuntimeError("L’ordre des rangs n’est pas respecté dans les profils équivalents.")
                report["checks"]["daily_groups_seniority_eight_hours"] = True
                report["checks"]["ortools_cp_sat_generation"] = True
                report["checks"]["offline_operations"] = True
                # Ne pas déclencher la sauvegarde à la fermeture du tableau de
                # bord : les seules données ici sont celles du dossier d'essai.
                release_gui()
        report["success"] = True
    except Exception as exc:
        report["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        release_gui()

    temporary = None
    try:
        output = Path(destination).resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=output.parent,
                                         prefix="verification-", suffix=".tmp", delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(report, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, output)
    except OSError as exc:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        if sys.stderr is not None:
            print(f"Impossible d'écrire le contrôle d'installation : {exc}", file=sys.stderr)
        return 1
    return 0 if report["success"] else 1
