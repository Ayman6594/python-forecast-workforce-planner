-- Schéma de base de données — sous-processus 2.3.3 « Ressources humaines et équipements »
-- ADAPTATION : SQLite au lieu de PostgreSQL (aucun serveur PostgreSQL disponible dans
-- l'environnement d'exécution de ce test). La logique métier (services/, ml/) est écrite
-- indépendamment du moteur de base ; porter ce schéma vers PostgreSQL (schema.sql cible
-- initial) ne demande que de réécrire ce fichier avec CREATE TYPE / IDENTITY / etc.

CREATE TABLE IF NOT EXISTS utilisateurs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    identifiant TEXT NOT NULL UNIQUE,
    nom TEXT NOT NULL,
    prenom TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('planificateur','responsable','direction','administrateur')),
    hash TEXT NOT NULL,
    sel TEXT NOT NULL,
    actif INTEGER NOT NULL DEFAULT 1,
    tentatives_echouees INTEGER NOT NULL DEFAULT 0,
    verrouille_jusqu_a TEXT
);

CREATE TABLE IF NOT EXISTS sites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL UNIQUE,
    adresse TEXT,
    actif INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS zones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site_id INTEGER NOT NULL REFERENCES sites(id),
    nom TEXT NOT NULL,
    type_equipement_principal TEXT NOT NULL,
    duree_poste_heures REAL NOT NULL CHECK (duree_poste_heures > 0),
    actif INTEGER NOT NULL DEFAULT 1,
    UNIQUE(site_id, nom)
);

CREATE TABLE IF NOT EXISTS equipements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site_id INTEGER NOT NULL REFERENCES sites(id),
    zone_id INTEGER NOT NULL REFERENCES zones(id),
    type TEXT NOT NULL,
    code TEXT NOT NULL UNIQUE,
    statut TEXT NOT NULL CHECK (statut IN ('disponible','maintenance','hors_service')),
    actif INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS indisponibilites_equipements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    equipement_id INTEGER NOT NULL REFERENCES equipements(id),
    date_debut TEXT NOT NULL,
    date_fin TEXT NOT NULL,
    motif TEXT
);

CREATE TABLE IF NOT EXISTS capacites_personnel (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site_id INTEGER NOT NULL REFERENCES sites(id),
    zone_id INTEGER NOT NULL REFERENCES zones(id),
    date TEXT NOT NULL,
    effectif_planifie INTEGER NOT NULL CHECK (effectif_planifie >= 0),
    UNIQUE(zone_id, date)
);

CREATE TABLE IF NOT EXISTS historique_activite (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site_id INTEGER NOT NULL REFERENCES sites(id),
    zone_id INTEGER NOT NULL REFERENCES zones(id),
    date TEXT NOT NULL,
    volume_traite REAL NOT NULL CHECK (volume_traite >= 0),
    effectif_present INTEGER NOT NULL CHECK (effectif_present >= 0),
    heures_travaillees REAL NOT NULL CHECK (heures_travaillees >= 0),
    heures_supplementaires REAL NOT NULL DEFAULT 0,
    heures_interim REAL NOT NULL DEFAULT 0,
    heures_absence REAL NOT NULL DEFAULT 0,
    heures_inactives REAL NOT NULL DEFAULT 0,
    equipements_mobilises INTEGER NOT NULL DEFAULT 0,
    heures_usage_equipement REAL NOT NULL DEFAULT 0,
    heures_disponibles_equipement REAL NOT NULL DEFAULT 0,
    heures_panne_equipement REAL NOT NULL DEFAULT 0,
    cout_rh REAL NOT NULL DEFAULT 0,
    commandes_a_temps INTEGER NOT NULL DEFAULT 0,
    commandes_totales INTEGER NOT NULL DEFAULT 0,
    indicateur_pic INTEGER NOT NULL DEFAULT 0,
    UNIQUE(zone_id, date)
);

CREATE TABLE IF NOT EXISTS previsions_volume (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site_id INTEGER NOT NULL REFERENCES sites(id),
    zone_id INTEGER NOT NULL REFERENCES zones(id),
    date TEXT NOT NULL,
    volume_prevu REAL NOT NULL CHECK (volume_prevu >= 0),
    source TEXT NOT NULL DEFAULT 'saisie',
    UNIQUE(zone_id, date)
);

CREATE TABLE IF NOT EXISTS modeles_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    methode TEXT NOT NULL CHECK (methode IN ('regression_lineaire','reseau_neurones')),
    zone_id INTEGER NOT NULL REFERENCES zones(id),
    cible TEXT NOT NULL CHECK (cible IN ('heures','equipements')),
    chemin_fichier TEXT NOT NULL,
    mae REAL, rmse REAL, mape REAL, biais REAL, couverture_ic REAL,
    actif INTEGER NOT NULL DEFAULT 0,
    date_creation TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS previsions_ressources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site_id INTEGER NOT NULL REFERENCES sites(id),
    zone_id INTEGER NOT NULL REFERENCES zones(id),
    date TEXT NOT NULL,
    version_modele_id INTEGER REFERENCES modeles_versions(id),
    methode TEXT NOT NULL CHECK (methode IN ('regression_lineaire','reseau_neurones')),
    heures REAL NOT NULL,
    effectif INTEGER NOT NULL,
    equipements INTEGER NOT NULL,
    ic_bas REAL, ic_haut REAL,
    date_generation TEXT NOT NULL,
    UNIQUE(zone_id, date, methode)
);

CREATE TABLE IF NOT EXISTS comparaisons_realise (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prevision_id INTEGER NOT NULL REFERENCES previsions_ressources(id),
    heures_reelles REAL,
    equipements_reels REAL,
    ecart_absolu REAL,
    ecart_relatif REAL,
    comparable INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS plans_charge (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site_id INTEGER NOT NULL REFERENCES sites(id),
    semaine TEXT NOT NULL,
    statut TEXT NOT NULL CHECK (statut IN ('brouillon','soumis','valide','rejete')) DEFAULT 'brouillon',
    commentaire TEXT,
    UNIQUE(site_id, semaine)
);

CREATE TABLE IF NOT EXISTS plans_charge_lignes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id INTEGER NOT NULL REFERENCES plans_charge(id),
    zone_id INTEGER NOT NULL REFERENCES zones(id),
    date TEXT NOT NULL,
    besoin_heures REAL NOT NULL,
    effectif_planifie INTEGER NOT NULL,
    interim_planifie INTEGER NOT NULL DEFAULT 0,
    equipements_planifies INTEGER NOT NULL,
    capacite_effectif INTEGER NOT NULL,
    capacite_equipements INTEGER NOT NULL,
    commentaire TEXT,
    UNIQUE(plan_id, zone_id, date)
);

CREATE TABLE IF NOT EXISTS kpi_valeurs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kpi_code TEXT NOT NULL,
    site_id INTEGER NOT NULL REFERENCES sites(id),
    zone_id INTEGER REFERENCES zones(id),
    periodicite TEXT NOT NULL CHECK (periodicite IN ('jour','semaine','mois','annee')),
    date_debut_periode TEXT NOT NULL,
    methode TEXT,
    valeur REAL,
    statut TEXT CHECK (statut IN ('vert','orange','rouge',NULL)),
    date_calcul TEXT NOT NULL,
    UNIQUE(kpi_code, zone_id, periodicite, date_debut_periode, methode)
);

CREATE TABLE IF NOT EXISTS alertes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL CHECK (type IN ('seuil_kpi','sous_effectif','sureffectif','penurie_equipement','derive_modele')),
    niveau TEXT NOT NULL CHECK (niveau IN ('orange','rouge')),
    kpi_code TEXT,
    site_id INTEGER NOT NULL REFERENCES sites(id),
    zone_id INTEGER REFERENCES zones(id),
    date_concernee TEXT,
    message TEXT NOT NULL,
    statut TEXT NOT NULL CHECK (statut IN ('ouverte','en_cours','resolue')) DEFAULT 'ouverte',
    assigne_a TEXT,
    action_menee TEXT,
    date_creation TEXT NOT NULL,
    date_maj TEXT NOT NULL
);
