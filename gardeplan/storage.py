"""Local append-only SQLite history. No networking, pickle, or external services."""
from __future__ import annotations

from copy import deepcopy
from contextlib import closing, contextmanager
from datetime import date, datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile

from .models import Week
from .branding import DISPLAY_NAME

SCHEMA_VERSION = "1"
STATUSES = {"draft", "validated", "published", "archived"}


class StorageError(ValueError):
    """A recoverable storage error suitable for a French error dialog."""


class Repository:
    def __init__(self, path: str | Path):
        self.path = Path(path).expanduser().resolve()
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self._connect() as conn:
                self._schema(conn)
        except (OSError, sqlite3.Error) as exc:
            raise StorageError(f"Impossible d’ouvrir la base locale : {exc}") from exc

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.path, timeout=15)
        try:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("PRAGMA synchronous=FULL")
            with conn:
                yield conn
        finally:
            conn.close()

    @staticmethod
    def _schema(conn):
        # Inspect the existing format before changing it. A future or unrelated
        # database must remain byte-for-byte untouched when we refuse to open it.
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
        if tables:
            if "metadata" not in tables:
                raise StorageError(f"Ce fichier SQLite n’est pas une base de {DISPLAY_NAME}. Choisissez une nouvelle base ou une sauvegarde compatible.")
            existing = conn.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()
            if not existing or existing[0] != SCHEMA_VERSION:
                raise StorageError("Cette base utilise une version non prise en charge. Conservez-la et mettez l’application à jour.")
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                monday TEXT NOT NULL,
                created_at TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('draft','validated','published','archived')),
                payload TEXT NOT NULL,
                checksum TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS versions_week ON versions(monday,id);
            CREATE TRIGGER IF NOT EXISTS versions_no_update BEFORE UPDATE ON versions
                BEGIN SELECT RAISE(ABORT, 'Versions are immutable'); END;
            CREATE TRIGGER IF NOT EXISTS versions_no_delete BEFORE DELETE ON versions
                BEGIN SELECT RAISE(ABORT, 'Versions are immutable'); END;
        """)
        existing = conn.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()
        if existing and existing[0] != SCHEMA_VERSION:
            raise StorageError("Cette base utilise une version non prise en charge. Conservez-la et mettez l’application à jour.")
        conn.execute("INSERT OR IGNORE INTO metadata VALUES ('schema_version', ?)", (SCHEMA_VERSION,))

    @staticmethod
    def _encode(week: Week) -> tuple[str, str]:
        # Round-trip through the strict model parser before persisting any snapshot.
        parsed = Week.from_dict(week.to_dict())
        day = date.fromisoformat(parsed.monday)
        if day.weekday() != 0:
            raise StorageError("La date de semaine doit être un lundi.")
        if parsed.status not in STATUSES:
            raise StorageError("Statut de semaine inconnu.")
        payload = json.dumps(parsed.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return payload, hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @staticmethod
    def _decode(row) -> Week:
        try:
            payload, checksum = row["payload"], row["checksum"]
            if not isinstance(payload, str) or not isinstance(checksum, str):
                raise ValueError("contenu de version invalide")
            if hashlib.sha256(payload.encode("utf-8")).hexdigest() != checksum:
                raise StorageError("Une version est endommagée. Restaurez une sauvegarde de sécurité.")
            week = Week.from_dict(json.loads(payload))
            if week.monday != row["monday"] or week.status != row["status"]:
                raise ValueError("en-tête différent du contenu")
            return week
        except StorageError:
            raise
        except (IndexError, TypeError, KeyError, ValueError) as exc:
            raise StorageError(f"La version sauvegardée ne peut pas être lue : {exc}") from exc

    def save(self, week: Week) -> int:
        """Append a complete snapshot. Invalid drafts remain saveable."""
        if week.status in {"validated", "published"}:
            from .validation import validate
            errors = [issue for issue in validate(week) if issue.severity == "error"]
            if errors:
                raise StorageError("L’horaire contient des erreurs bloquantes. Sauvegardez-le en brouillon ou corrigez les alertes avant de le valider ou publier.")
        try:
            payload, checksum = self._encode(week)
            with self._connect() as conn:
                last = conn.execute("SELECT id,checksum FROM versions WHERE monday=? ORDER BY id DESC LIMIT 1", (week.monday,)).fetchone()
                if last and last["checksum"] == checksum:
                    return last["id"]
                cur = conn.execute(
                    "INSERT INTO versions(monday,created_at,status,payload,checksum) VALUES(?,?,?,?,?)",
                    (week.monday, datetime.now(timezone.utc).isoformat(timespec="microseconds"), week.status, payload, checksum),
                )
                return cur.lastrowid
        except (OSError, sqlite3.Error, TypeError, ValueError) as exc:
            raise StorageError(f"L’horaire n’a pas pu être sauvegardé : {exc}") from exc

    def load_week(self, monday: str) -> Week | None:
        try:
            with self._connect() as conn:
                row = conn.execute("SELECT * FROM versions WHERE monday=? ORDER BY id DESC LIMIT 1", (monday,)).fetchone()
                return self._decode(row) if row else None
        except sqlite3.Error as exc:
            raise StorageError(f"Impossible de lire cette semaine : {exc}") from exc

    def load_version(self, version_id: int) -> Week:
        try:
            with self._connect() as conn:
                row = conn.execute("SELECT * FROM versions WHERE id=?", (version_id,)).fetchone()
                if not row:
                    raise StorageError("Cette version n’existe plus dans cette base.")
                return self._decode(row)
        except sqlite3.Error as exc:
            raise StorageError(f"Impossible de lire cette version : {exc}") from exc

    def latest_week(self) -> Week | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM versions ORDER BY id DESC LIMIT 1").fetchone()
            return self._decode(row) if row else None

    def history(self, monday: str) -> list[dict]:
        with self._connect() as conn:
            return [dict(row) for row in conn.execute(
                "SELECT id,monday,created_at,status FROM versions WHERE monday=? ORDER BY id DESC", (monday,)
            )]

    def list_weeks(self) -> list[dict]:
        with self._connect() as conn:
            return [dict(row) for row in conn.execute("""
                SELECT v.id,v.monday,v.created_at,v.status FROM versions v
                JOIN (SELECT monday,MAX(id) id FROM versions GROUP BY monday) last ON v.id=last.id
                ORDER BY v.monday DESC
            """)]

    def restore(self, version_id: int) -> Week:
        week = self.load_version(version_id)
        week.status = "draft"
        self.save(week)
        return week

    def duplicate(self, week: Week, new_monday: str) -> Week:
        if self.load_week(new_monday) is not None:
            raise StorageError("Cette semaine existe déjà. Choisissez une semaine vide afin de préserver son horaire.")
        result = deepcopy(week)
        result.monday, result.status = new_monday, "draft"
        self.save(result)
        return result

    def backup(self, destination: str | Path) -> Path:
        """SQLite's online backup API creates a consistent copy, atomically."""
        destination = Path(destination).expanduser().resolve()
        if destination == self.path:
            raise StorageError("Choisissez un autre fichier que la base utilisée par l’application.")
        temporary = None
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            fd, temporary = tempfile.mkstemp(prefix=".gardeplan-backup-", suffix=".sqlite3", dir=destination.parent)
            os.close(fd)
            with self._connect() as source, closing(sqlite3.connect(temporary)) as target:
                source.backup(target)
                if target.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise StorageError("La copie de sécurité n’a pas pu être vérifiée.")
            os.replace(temporary, destination)
            temporary = None
            return destination
        except (OSError, sqlite3.Error) as exc:
            raise StorageError(f"Impossible de créer la sauvegarde de sécurité : {exc}") from exc
        finally:
            if temporary and os.path.exists(temporary):
                os.unlink(temporary)

    def import_backup(self, source: str | Path) -> Path:
        """Validate all rows, recreate known schema, preserve the previous database."""
        source = Path(source).expanduser().resolve()
        if source == self.path:
            raise StorageError("Ce fichier est déjà la base ouverte.")
        temporary = None
        try:
            if source.stat().st_size > 512 * 1024 * 1024:
                raise StorageError("Cette sauvegarde dépasse la limite de 512 Mo.")
            # mode=ro also prevents creation when the selected file is missing.
            with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as incoming:
                incoming.row_factory = sqlite3.Row
                if incoming.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise StorageError("Le fichier choisi est endommagé.")
                schema = incoming.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()
                if not schema or schema[0] != SCHEMA_VERSION:
                    raise StorageError(f"Ce fichier n’est pas une sauvegarde compatible avec {DISPLAY_NAME}.")
                fd, temporary = tempfile.mkstemp(prefix=".gardeplan-import-", suffix=".sqlite3", dir=self.path.parent)
                os.close(fd)
                with closing(sqlite3.connect(temporary)) as target:
                    self._schema(target)
                    for row in incoming.execute("SELECT * FROM versions ORDER BY id"):
                        if len(row["payload"]) > 10 * 1024 * 1024:
                            raise StorageError("Une version de la sauvegarde est trop volumineuse.")
                        week = self._decode(row)
                        self._encode(week)
                        target.execute("INSERT INTO versions(id,monday,created_at,status,payload,checksum) VALUES(?,?,?,?,?,?)", tuple(row[key] for key in ("id", "monday", "created_at", "status", "payload", "checksum")))
                    target.commit()
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
            safety = self.path.with_name(f"{self.path.stem}-avant-import-{stamp}.sqlite3")
            self.backup(safety)
            os.replace(temporary, self.path)
            temporary = None
            return safety
        except StorageError:
            raise
        except (OSError, sqlite3.Error, ValueError, KeyError, TypeError) as exc:
            raise StorageError(f"La sauvegarde n’a pas été importée. La base actuelle est conservée : {exc}") from exc
        finally:
            if temporary and os.path.exists(temporary):
                os.unlink(temporary)
