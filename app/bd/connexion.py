"""Connexion à la base de données (SQLite pour ce test — voir schema.sql)."""
import sqlite3
from pathlib import Path

CHEMIN_BASE = Path(__file__).resolve().parents[2] / "donnees.db"


def obtenir_connexion(chemin=None):
    conn = sqlite3.connect(chemin or CHEMIN_BASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialiser_base(chemin=None, recreer=False):
    chemin = Path(chemin or CHEMIN_BASE)
    if recreer and chemin.exists():
        chemin.unlink()
    conn = obtenir_connexion(chemin)
    schema = (Path(__file__).parent / "schema.sql").read_text(encoding="utf-8")
    conn.executescript(schema)
    conn.commit()
    return conn
