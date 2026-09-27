"""UC18 Émettre une alerte, à partir du plan de charge des lignes (sous/sur-effectif, pénurie)."""
from datetime import date


def _upsert_alerte(conn, type_, niveau, site_id, zone_id, date_concernee, message):
    existante = conn.execute(
        "SELECT id FROM alertes WHERE type=? AND site_id=? AND zone_id=? AND date_concernee=? AND statut!='resolue'",
        (type_, site_id, zone_id, date_concernee)).fetchone()
    if existante:
        conn.execute("UPDATE alertes SET niveau=?, message=?, date_maj=date('now') WHERE id=?",
                     (niveau, message, existante["id"]))
        return existante["id"]
    cur = conn.execute("""INSERT INTO alertes (type, niveau, site_id, zone_id, date_concernee, message,
        statut, date_creation, date_maj) VALUES (?,?,?,?,?,?, 'ouverte', date('now'), date('now'))""",
        (type_, niveau, site_id, zone_id, date_concernee, message))
    return cur.lastrowid


def generer_alertes_capacite(conn, site_id, lignes_plan_df):
    """lignes_plan_df : sortie de elaborer_plan_charge (zone, date, besoin/capacité effectif+équipements)."""
    creees = []
    aujourdhui = date.today()
    for _, ligne in lignes_plan_df.iterrows():
        d = date.fromisoformat(ligne["date"])
        jours_avance = (d - aujourdhui).days
        zone_id = None  # rempli par l'appelant si nécessaire ; ici on garde le nom pour le message
        adequation = ligne["adequation_pct"]

        if adequation < 90 and jours_avance <= 7:
            niveau = "rouge" if jours_avance <= 2 else "orange"
            msg = f"Sous-effectif prévisionnel en {ligne['zone']} le {d.strftime('%d/%m/%Y')} (adéquation {adequation:.0f} %)."
            creees.append(_upsert_alerte(conn, "sous_effectif", niveau, site_id, zone_id, ligne["date"], msg))
        elif adequation > 110:
            msg = f"Sureffectif prévisionnel en {ligne['zone']} le {d.strftime('%d/%m/%Y')} (adéquation {adequation:.0f} %)."
            creees.append(_upsert_alerte(conn, "sureffectif", "orange", site_id, zone_id, ligne["date"], msg))

        if ligne["besoin_equipements"] > ligne["capacite_equipements"]:
            msg = (f"Pénurie d'équipements en {ligne['zone']} le {d.strftime('%d/%m/%Y')} : "
                   f"besoin {ligne['besoin_equipements']}, disponibles {ligne['capacite_equipements']}.")
            creees.append(_upsert_alerte(conn, "penurie_equipement", "rouge", site_id, zone_id, ligne["date"], msg))
    conn.commit()
    return creees


def traiter_alerte(conn, alerte_id, action=None, nouveau_statut="en_cours"):
    if nouveau_statut == "resolue" and not action:
        raise ValueError("L'action menée est obligatoire pour clôturer une alerte.")
    conn.execute("UPDATE alertes SET statut=?, action_menee=COALESCE(?, action_menee), date_maj=date('now') WHERE id=?",
                 (nouveau_statut, action, alerte_id))
    conn.commit()
