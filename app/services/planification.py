"""UC11 Générer les prévisions de ressources ; UC12 Élaborer le plan de charge."""
import pandas as pd
from datetime import date, timedelta
from app.ml.entrainement import entrainer, predire, heures_vers_effectif, vers_equipements


def generer_previsions_ressources(conn, site_id, zones: dict, horizon_jours=14):
    """Entraîne RL+RN sur l'historique et génère les prévisions d'heures/effectif/équipements
    par zone pour les `horizon_jours` prochains jours, à partir des prévisions de volume saisies.
    Retourne un dict {nom_zone: DataFrame} et enregistre en base."""
    resultats = {}
    aujourdhui = date.today()
    horizon = [aujourdhui + timedelta(days=i) for i in range(1, horizon_jours + 1)]

    for nom_zone, zone_id in zones.items():
        hist = pd.read_sql_query(
            "SELECT date, volume_traite AS volume, indicateur_pic, "
            "(heures_travaillees - heures_inactives) AS heures_necessaires, "
            "equipements_mobilises FROM historique_activite WHERE zone_id=? ORDER BY date",
            conn, params=(zone_id,))
        if len(hist) < 30:
            continue

        previsions_vol = pd.read_sql_query(
            "SELECT date, volume_prevu FROM previsions_volume WHERE zone_id=? AND date>=? ORDER BY date",
            conn, params=(zone_id, aujourdhui.isoformat()))
        previsions_vol["indicateur_pic"] = 0
        previsions_vol = previsions_vol[pd.to_datetime(previsions_vol["date"]).dt.date.isin(horizon)]
        if previsions_vol.empty:
            continue

        duree_poste = conn.execute("SELECT duree_poste_heures FROM zones WHERE id=?", (zone_id,)).fetchone()[0]
        modeles_heures = entrainer(hist, "volume", "heures_necessaires")
        modeles_eqp = entrainer(hist, "volume", "equipements_mobilises")

        lignes = []
        for methode in ("regression_lineaire", "reseau_neurones"):
            heures_pred = predire(modeles_heures[methode]["pipeline"], modeles_heures[methode]["quantiles_residus"], previsions_vol)
            eqp_pred = predire(modeles_eqp[methode]["pipeline"], modeles_eqp[methode]["quantiles_residus"], previsions_vol)
            for i in range(len(heures_pred)):
                h = heures_pred.iloc[i]
                e = eqp_pred.iloc[i]
                effectif = heures_vers_effectif(h["prediction"], duree_poste)
                equipements = vers_equipements(e["prediction"])
                lignes.append({
                    "date": h["date"].isoformat(), "methode": methode,
                    "heures": round(h["prediction"], 2), "effectif": effectif, "equipements": equipements,
                    "ic_bas": round(h["ic_bas"], 2), "ic_haut": round(h["ic_haut"], 2),
                })
                conn.execute("""INSERT OR REPLACE INTO previsions_ressources
                    (site_id, zone_id, date, methode, heures, effectif, equipements, ic_bas, ic_haut, date_generation)
                    VALUES (?,?,?,?,?,?,?,?,?, date('now'))""",
                    (site_id, zone_id, h["date"].isoformat(), methode, round(h["prediction"], 2), effectif,
                     equipements, round(h["ic_bas"], 2), round(h["ic_haut"], 2)))
        conn.commit()
        resultats[nom_zone] = pd.DataFrame(lignes)
    return resultats


def elaborer_plan_charge(conn, site_id, zones: dict, lundi: date, methode_active="regression_lineaire", nb_jours=7):
    """UC12 : propose le plan de charge d'une semaine à partir du modèle actif,
    comparé à la capacité (personnel planifié, équipements disponibles moins maintenance)."""
    conn.execute("INSERT OR IGNORE INTO plans_charge (site_id, semaine, statut) VALUES (?,?, 'brouillon')",
                 (site_id, lundi.isoformat()))
    plan_id = conn.execute(
        "SELECT id FROM plans_charge WHERE site_id=? AND semaine=?", (site_id, lundi.isoformat())).fetchone()[0]

    lignes = []
    for nom_zone, zone_id in zones.items():
        duree_poste = conn.execute("SELECT duree_poste_heures FROM zones WHERE id=?", (zone_id,)).fetchone()[0]
        nb_equipements_zone = conn.execute("SELECT COUNT(*) FROM equipements WHERE zone_id=? AND actif=1", (zone_id,)).fetchone()[0]

        for offset in range(nb_jours):
            d = lundi + timedelta(days=offset)
            prev = conn.execute(
                "SELECT heures, effectif, equipements FROM previsions_ressources WHERE zone_id=? AND date=? AND methode=?",
                (zone_id, d.isoformat(), methode_active)).fetchone()
            if not prev:
                continue
            besoin_heures, besoin_effectif, besoin_eqp = prev["heures"], prev["effectif"], prev["equipements"]

            cap_row = conn.execute("SELECT effectif_planifie FROM capacites_personnel WHERE zone_id=? AND date=?",
                                    (zone_id, d.isoformat())).fetchone()
            capacite_effectif = cap_row[0] if cap_row else 0

            indispo = conn.execute(
                "SELECT COUNT(*) FROM indisponibilites_equipements ie JOIN equipements e ON ie.equipement_id=e.id "
                "WHERE e.zone_id=? AND ? BETWEEN ie.date_debut AND ie.date_fin", (zone_id, d.isoformat())).fetchone()[0]
            capacite_equipements = max(0, nb_equipements_zone - indispo)

            interim = max(0, besoin_effectif - capacite_effectif)
            depassement = besoin_effectif > capacite_effectif or besoin_eqp > capacite_equipements
            adequation_pct = (capacite_effectif * duree_poste / besoin_heures * 100) if besoin_heures > 0 else 100

            conn.execute("""INSERT OR REPLACE INTO plans_charge_lignes
                (plan_id, zone_id, date, besoin_heures, effectif_planifie, interim_planifie,
                 equipements_planifies, capacite_effectif, capacite_equipements, commentaire)
                VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (plan_id, zone_id, d.isoformat(), besoin_heures, min(besoin_effectif, capacite_effectif),
                 interim, min(besoin_eqp, capacite_equipements), capacite_effectif, capacite_equipements,
                 "Dépassement de capacité" if depassement else None))
            lignes.append({
                "zone": nom_zone, "date": d.isoformat(), "besoin_effectif": besoin_effectif,
                "capacite_effectif": capacite_effectif, "besoin_equipements": besoin_eqp,
                "capacite_equipements": capacite_equipements, "depassement": depassement,
                "adequation_pct": round(adequation_pct, 1),
            })
    conn.commit()
    return plan_id, pd.DataFrame(lignes)
