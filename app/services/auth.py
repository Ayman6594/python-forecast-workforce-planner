"""UC01 S'authentifier (version condensée : verrouillage 5 échecs / 15 min)."""
import hashlib
import hmac
import os
from datetime import datetime, timedelta

ITERATIONS = 200_000


def hacher_mot_de_passe(mot_de_passe: str, sel: bytes = None):
    sel = sel or os.urandom(16)
    h = hashlib.pbkdf2_hmac("sha256", mot_de_passe.encode("utf-8"), sel, ITERATIONS)
    return h.hex(), sel.hex()


def creer_utilisateur(conn, identifiant, nom, prenom, role, mot_de_passe):
    h, sel = hacher_mot_de_passe(mot_de_passe)
    conn.execute("""INSERT OR REPLACE INTO utilisateurs (identifiant, nom, prenom, role, hash, sel, actif)
        VALUES (?,?,?,?,?,?,1)""", (identifiant, nom, prenom, role, h, sel))
    conn.commit()


def authentifier(conn, identifiant, mot_de_passe):
    """Retourne (succès: bool, message: str, utilisateur: dict|None). Message générique en échec."""
    MESSAGE_ECHEC = "Identifiant ou mot de passe incorrect."
    row = conn.execute("SELECT * FROM utilisateurs WHERE identifiant=?", (identifiant,)).fetchone()
    if row is None:
        return False, MESSAGE_ECHEC, None
    if not row["actif"]:
        return False, "Ce compte est désactivé.", None
    if row["verrouille_jusqu_a"]:
        if datetime.fromisoformat(row["verrouille_jusqu_a"]) > datetime.now():
            return False, "Compte verrouillé temporairement (trop d'échecs). Réessayez dans quelques minutes.", None

    h_calcule, _ = hacher_mot_de_passe(mot_de_passe, bytes.fromhex(row["sel"]))
    if hmac.compare_digest(h_calcule, row["hash"]):
        conn.execute("UPDATE utilisateurs SET tentatives_echouees=0, verrouille_jusqu_a=NULL WHERE id=?", (row["id"],))
        conn.commit()
        return True, "Connexion réussie.", dict(row)

    tentatives = row["tentatives_echouees"] + 1
    verrouillage = (datetime.now() + timedelta(minutes=15)).isoformat() if tentatives >= 5 else None
    conn.execute("UPDATE utilisateurs SET tentatives_echouees=?, verrouille_jusqu_a=? WHERE id=?",
                 (tentatives, verrouillage, row["id"]))
    conn.commit()
    return False, MESSAGE_ECHEC, None
