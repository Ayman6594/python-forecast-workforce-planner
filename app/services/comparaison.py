"""UC20 Comparer le réalisé aux prévisions RL et RN ; UC21 Détecter une dérive."""
import numpy as np
import pandas as pd


def comparer_realise_vs_previsions(conn, zone_id, date_debut, date_fin):
    previsions = pd.read_sql_query(
        "SELECT id, date, methode, heures, equipements FROM previsions_ressources "
        "WHERE zone_id=? AND date BETWEEN ? AND ?", conn, params=(zone_id, date_debut, date_fin))
    reel = pd.read_sql_query(
        "SELECT date, (heures_travaillees - heures_inactives) AS heures_reelles, "
        "equipements_mobilises AS equipements_reels FROM historique_activite WHERE zone_id=? AND date BETWEEN ? AND ?",
        conn, params=(zone_id, date_debut, date_fin))
    fusion = previsions.merge(reel, on="date", how="left")
    fusion["comparable"] = fusion["heures_reelles"].notna()
    fusion["ecart_absolu"] = (fusion["heures"] - fusion["heures_reelles"]).abs()
    fusion["ecart_relatif"] = np.where(
        fusion["heures_reelles"].fillna(0) != 0, fusion["ecart_absolu"] / fusion["heures_reelles"] * 100, np.nan)

    metriques = {}
    for methode, grp in fusion[fusion["comparable"]].groupby("methode"):
        residus = grp["heures"] - grp["heures_reelles"]
        mae = residus.abs().mean()
        rmse = np.sqrt((residus ** 2).mean())
        mask = grp["heures_reelles"] != 0
        mape = (residus[mask].abs() / grp.loc[mask, "heures_reelles"]).mean() * 100 if mask.any() else None
        biais = residus.sum() / grp["heures_reelles"].sum() * 100 if grp["heures_reelles"].sum() else None
        metriques[methode] = {"mae": round(mae, 2), "rmse": round(rmse, 2),
                               "mape": round(mape, 2) if mape is not None else None,
                               "biais": round(biais, 2) if biais is not None else None}

    if set(metriques) == {"regression_lineaire", "reseau_neurones"}:
        pivot = fusion[fusion["comparable"]].pivot_table(index="date", columns="methode", values="ecart_absolu")
        victoires = (pivot["regression_lineaire"] < pivot["reseau_neurones"]).sum()
        total = pivot.dropna().shape[0]
        if total:
            metriques["regression_lineaire"]["taux_victoire"] = round(victoires / total * 100, 1)
            metriques["reseau_neurones"]["taux_victoire"] = round(100 - victoires / total * 100, 1)
    return fusion, metriques


def detecter_derive(conn, site_id, zone_id, methode_active, seuil_mape=10.0, nb_semaines=8):
    """UC21 : dérive si le MAPE hebdomadaire du modèle actif dépasse le seuil 2 semaines de suite."""
    hist = pd.read_sql_query(
        "SELECT date FROM historique_activite WHERE zone_id=? ORDER BY date DESC LIMIT 1", conn, params=(zone_id,))
    if hist.empty:
        return False, []
    fin = pd.to_datetime(hist["date"].iloc[0])
    mapes_hebdo = []
    for s in range(nb_semaines):
        debut_s = (fin - pd.Timedelta(days=7 * (s + 1) - 1)).date().isoformat()
        fin_s = (fin - pd.Timedelta(days=7 * s)).date().isoformat()
        _, metriques = comparer_realise_vs_previsions(conn, zone_id, debut_s, fin_s)
        mape = metriques.get(methode_active, {}).get("mape")
        mapes_hebdo.append(mape)
    mapes_hebdo = list(reversed(mapes_hebdo))  # ordre chronologique

    derive = False
    for i in range(len(mapes_hebdo) - 1):
        a, b = mapes_hebdo[i], mapes_hebdo[i + 1]
        if a is not None and b is not None and a > seuil_mape and b > seuil_mape:
            derive = True
    if derive:
        conn.execute("""INSERT INTO alertes (type, niveau, site_id, zone_id, message, statut, date_creation, date_maj)
            VALUES ('derive_modele','orange', ?, ?, ?, 'ouverte', date('now'), date('now'))""",
            (site_id, zone_id, f"Dérive du modèle {methode_active} : MAPE > {seuil_mape}% sur 2 semaines consécutives. "
                                f"Réentraînement recommandé."))
        conn.commit()
    return derive, mapes_hebdo
