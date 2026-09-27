"""Génère un jeu de données de démonstration reproductible (graine 42)."""
import random
import math
from datetime import date, timedelta

GRAINE = 42
DUREE_POSTE = 7.5
JOURS_HISTORIQUE = 18 * 30  # 18 mois


def prochain_lundi(d):
    return d + timedelta(days=(7 - d.weekday()) % 7 or 7)


def creer_site_et_zones(conn):
    cur = conn.execute("INSERT INTO sites (nom, adresse, actif) VALUES (?,?,1)",
                        ("Plateforme Casablanca", "Zone industrielle, Casablanca"))
    site_id = cur.lastrowid
    zones = {}
    for nom, eqp in [("Réception", "chariot_elevateur"), ("Stockage", "chariot_elevateur"),
                      ("Préparation", "transpalette_electrique"), ("Expédition", "transpalette_electrique")]:
        cur = conn.execute(
            "INSERT INTO zones (site_id, nom, type_equipement_principal, duree_poste_heures, actif) VALUES (?,?,?,?,1)",
            (site_id, nom, eqp, DUREE_POSTE))
        zones[nom] = cur.lastrowid

    # équipements : 8 chariots élévateurs (Réception/Stockage), 10 transpalettes (Préparation/Expédition)
    compteur = 1
    for nom_zone, type_eqp, nb in [("Réception", "chariot_elevateur", 4), ("Stockage", "chariot_elevateur", 4),
                                     ("Préparation", "transpalette_electrique", 5), ("Expédition", "transpalette_electrique", 5)]:
        for _ in range(nb):
            code = f"EQ-{compteur:03d}"
            conn.execute(
                "INSERT INTO equipements (site_id, zone_id, type, code, statut, actif) VALUES (?,?,?,?, 'disponible',1)",
                (site_id, zones[nom_zone], type_eqp, code))
            compteur += 1
    conn.commit()
    return site_id, zones


def _volume_base(jour_semaine, mois, indice_jour, rng):
    base = 1000
    facteur_semaine = {0: 1.25, 1: 1.0, 2: 1.0, 3: 1.3, 4: 1.05, 5: 0.6, 6: 0.3}[jour_semaine]
    facteur_annuel = 1 + 0.35 * math.sin((mois - 1) / 12 * 2 * math.pi - math.pi / 2) * 0.5 + 0.15
    bruit = rng.gauss(0, 0.06)
    return max(0, base * facteur_semaine * facteur_annuel * (1 + bruit))


def generer_historique(conn, site_id, zones):
    rng = random.Random(GRAINE)
    aujourdhui = date.today()
    debut = aujourdhui - timedelta(days=JOURS_HISTORIQUE)
    capacite_effectif = {"Réception": 6, "Stockage": 5, "Préparation": 8, "Expédition": 7}
    campagnes = set()
    # quelques campagnes promo ponctuelles historiques (+30 à 50%)
    for _ in range(12):
        campagnes.add(debut + timedelta(days=rng.randint(0, JOURS_HISTORIQUE)))

    for i in range(JOURS_HISTORIQUE):
        d = debut + timedelta(days=i)
        pic = d in campagnes
        for nom_zone, zone_id in zones.items():
            vol = _volume_base(d.weekday(), d.month, i, rng)
            if pic:
                vol *= rng.uniform(1.3, 1.5)
            cap = capacite_effectif[nom_zone]
            # capacité de personnel figée par jour de semaine (même planning chaque semaine)
            effectif_planifie = cap
            conn.execute(
                "INSERT OR IGNORE INTO capacites_personnel (site_id, zone_id, date, effectif_planifie) VALUES (?,?,?,?)",
                (site_id, zone_id, d.isoformat(), effectif_planifie))

            productivite_nominale = 27  # unités/heure/personne, calibré pour ~80% de la capacité un jour moyen
            charge_relative = vol / (cap * DUREE_POSTE * productivite_nominale)
            # effet non linéaire de congestion au-delà de 85% de capacité
            productivite = productivite_nominale if charge_relative <= 0.85 else productivite_nominale * (0.85 / charge_relative) ** 0.6
            heures_necessaires = vol / max(productivite, 40)
            effectif_present = min(cap, round(heures_necessaires / DUREE_POSTE) or cap)
            heures_dispo_effectif = effectif_planifie * DUREE_POSTE
            depassement_besoin = max(0, heures_necessaires - heures_dispo_effectif)
            heures_sup = depassement_besoin * 0.6
            heures_interim = depassement_besoin * 0.4
            heures_inactives = max(0, heures_dispo_effectif - heures_necessaires)
            # Construit pour que heures_travaillees - heures_inactives == heures_necessaires (formule UC20/KPI)
            heures_travaillees = heures_dispo_effectif + heures_sup + heures_interim
            heures_absence = rng.uniform(0, 0.5) * DUREE_POSTE if rng.random() < 0.1 else 0

            nb_eqp_zone = 4 if nom_zone in ("Réception", "Stockage") else 5
            eqp_necessaires = min(nb_eqp_zone, math.ceil(heures_necessaires / (DUREE_POSTE * 0.9)) or 1)
            heures_dispo_eqp = nb_eqp_zone * DUREE_POSTE
            heures_panne = rng.uniform(0, 0.5) if rng.random() < 0.05 else 0
            heures_usage = min(heures_dispo_eqp - heures_panne, eqp_necessaires * DUREE_POSTE * 0.85)

            cout_rh = heures_travaillees * 35 + heures_sup * 52 + heures_interim * 45
            commandes_totales = max(1, round(vol / 12))
            retard_ratio = 0.02 if charge_relative <= 0.9 else min(0.25, (charge_relative - 0.9) * 1.5)
            commandes_a_temps = round(commandes_totales * (1 - retard_ratio))

            conn.execute("""INSERT OR REPLACE INTO historique_activite
                (site_id, zone_id, date, volume_traite, effectif_present, heures_travaillees,
                 heures_supplementaires, heures_interim, heures_absence, heures_inactives,
                 equipements_mobilises, heures_usage_equipement, heures_disponibles_equipement,
                 heures_panne_equipement, cout_rh, commandes_a_temps, commandes_totales, indicateur_pic)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (site_id, zone_id, d.isoformat(), round(vol, 1), effectif_present, round(heures_travaillees, 2),
                 round(heures_sup, 2), round(heures_interim, 2), round(heures_absence, 2), round(heures_inactives, 2),
                 eqp_necessaires, round(heures_usage, 2), round(heures_dispo_eqp, 2), round(heures_panne, 2),
                 round(cout_rh, 2), commandes_a_temps, commandes_totales, int(pic)))
    conn.commit()
    return debut, aujourdhui


def generer_semaine_demo(conn, site_id, zones):
    """Semaine suivante : pic +40% jeudi, 2 chariots en maintenance lun-ven, mardi suivant faible."""
    lundi = prochain_lundi(date.today())
    rng = random.Random(GRAINE + 1)
    capacite_effectif = {"Réception": 6, "Stockage": 5, "Préparation": 8, "Expédition": 7}
    for offset in range(14):  # cette semaine + la suivante (mardi faible)
        d = lundi + timedelta(days=offset)
        for nom_zone, zone_id in zones.items():
            # « le même planning que la semaine précédente » : capacité figée, non ajustée au pic
            conn.execute(
                "INSERT OR IGNORE INTO capacites_personnel (site_id, zone_id, date, effectif_planifie) VALUES (?,?,?,?)",
                (site_id, zone_id, d.isoformat(), capacite_effectif[nom_zone]))
            vol = _volume_base(d.weekday(), d.month, offset, rng)
            if d.weekday() == 3 and offset < 7:  # jeudi de la semaine de démo
                vol *= 1.55
            if d.weekday() == 1 and offset >= 7:  # mardi suivant : volume faible
                vol *= 0.55
            conn.execute("INSERT OR REPLACE INTO previsions_volume (site_id, zone_id, date, volume_prevu, source) VALUES (?,?,?,?,'demo')",
                         (site_id, zone_id, d.isoformat(), round(vol, 1)))

    # 2 chariots élévateurs en maintenance du lundi au vendredi de la semaine de démo
    vendredi = lundi + timedelta(days=4)
    chariots = conn.execute(
        "SELECT e.id FROM equipements e JOIN zones z ON e.zone_id=z.id WHERE z.type_equipement_principal='chariot_elevateur' LIMIT 2").fetchall()
    for row in chariots:
        conn.execute("INSERT INTO indisponibilites_equipements (equipement_id, date_debut, date_fin, motif) VALUES (?,?,?,?)",
                     (row["id"], lundi.isoformat(), vendredi.isoformat(), "Maintenance planifiée"))
    conn.commit()
    return lundi


def generer_jeu_complet(conn):
    from app.services.auth import creer_utilisateur
    site_id, zones = creer_site_et_zones(conn)
    generer_historique(conn, site_id, zones)
    lundi_demo = generer_semaine_demo(conn, site_id, zones)
    for identifiant, nom, prenom, role in [
        ("admin", "Administrateur", "Système", "administrateur"),
        ("planif", "Planificateur", "Demo", "planificateur"),
        ("resp", "Responsable", "Demo", "responsable"),
        ("direction", "Direction", "Demo", "direction"),
    ]:
        creer_utilisateur(conn, identifiant, nom, prenom, role, "demo1234")
    return site_id, zones, lundi_demo
