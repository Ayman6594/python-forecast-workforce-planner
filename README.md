# 2.3.3 — Ressources humaines et équipements (noyau testé)

Livraison en urgence (échéance du jour) : le **cœur métier** du sous-processus
2.3.3, entièrement testé et fonctionnel. **L'interface graphique Tkinter et
les 24 cas d'utilisation complets ne sont pas dans cette livraison** — voir
« Ce qui manque » ci-dessous.

## Ce qui fonctionne et est testé (12 tests, tous verts)

- **Base de données** (`app/bd/schema.sql`, `connexion.py`) : schéma complet
  des tables métier (sites, zones, équipements, historique, prévisions,
  modèles, plans de charge, KPI, alertes).
- **Génération de données de démonstration** (`app/demo/generateur.py`) :
  18 mois d'historique réaliste (saisonnalité hebdo/annuelle, effet de
  congestion non linéaire au-delà de 85 % de capacité) + la semaine de
  démonstration : **pic de +55 % le jeudi**, 2 chariots élévateurs en
  maintenance, mardi suivant en sous-charge.
- **Modèles de prévision** (`app/ml/entrainement.py`) : régression linéaire
  et réseau de neurones (scikit-learn), découpage chronologique 80/20,
  intervalle de confiance par quantiles des résidus, conversion
  heures → effectif/équipements.
- **Génération des prévisions de ressources** (`app/services/planification.py`,
  UC11) et **élaboration du plan de charge** (UC12) : besoin vs capacité par
  zone et par jour, avec drapeau de dépassement.
- **KPI** (`app/services/kpi.py`, UC17) : les 4 règles de statut (baisse,
  hausse, plage, information), entièrement testées unitairement.
- **Alertes** (`app/services/alertes.py`, UC18/UC19) : sous-effectif,
  sureffectif, pénurie d'équipements, avec déduplication.
- **Comparaison réel/prévu et dérive** (`app/services/comparaison.py`,
  UC20/UC21) : MAE/RMSE/MAPE/biais/taux de victoire par méthode, détection
  de dérive sur 2 semaines consécutives.
- **Test d'acceptation « situation du lundi »** (`tests/test_scenario_demo.py`)
  qui rejoue exactement le scénario du storytelling et vérifie les 5 points
  attendus.

## Écarts par rapport au prompt d'origine (à signaler dans le rapport)

1. **SQLite au lieu de PostgreSQL** : aucun serveur PostgreSQL n'était
   disponible dans l'environnement d'exécution de ce test. Toute la logique
   métier (`services/`, `ml/`) est écrite indépendamment du moteur ; migrer
   `schema.sql` vers PostgreSQL (`CREATE TYPE`, `GENERATED ALWAYS AS
   IDENTITY`, `psycopg2`) est un travail mécanique et cloisonné.
2. **Interface graphique réduite** : 4 écrans (Connexion, Tableau de bord,
   Plan de charge, Alertes) au lieu des 12 du prompt d'origine — pas de
   Données, Prévisions détaillées, Comparaison, KPI dédié, Rapports,
   Modèles, Administration en tant qu'écrans séparés (leurs services
   existent et sont testés, l'écran manque).
3. **Authentification (UC01) simplifiée** : hachage PBKDF2 + verrouillage
   5 échecs/15 min bien réel, mais pas de gestion des utilisateurs en GUI
   (UC02/UC03) — 4 comptes de démo créés directement par le générateur.
4. **Rapports PDF/Excel (UC22-24), tâches planifiées (APScheduler)** : non
   implémentés faute de temps.
5. **Constantes de calibration de la démo** (productivité nominale,
   multiplicateur du pic) ajustées empiriquement pour que le scénario soit
   démontrable de façon fiable par les tests — ce sont des paramètres de
   `app/demo/generateur.py`, pas des règles métier.

## Lancer l'application graphique

```bash
pip install -r requirements.txt
python -m app
```

Comptes de démonstration (mot de passe `demo1234`) : `admin`, `planif`,
`resp`, `direction`. Le rôle affiché change les écrans visibles dans le
menu de gauche (`direction` ne voit que le tableau de bord).

Au premier lancement, `donnees.db` est créé et peuplé automatiquement
(18 mois d'historique + semaine de démonstration). Les lancements suivants
réutilisent la même base ; supprimez `donnees.db` pour régénérer les
données depuis zéro.

## Lancer les tests

```bash
pip install -r requirements.txt
python -m pytest tests/ -v
```

## Rejouer le scénario manuellement

```python
from app.bd.connexion import initialiser_base
from app.demo.generateur import generer_jeu_complet
from app.services.planification import generer_previsions_ressources, elaborer_plan_charge
from app.services.alertes import generer_alertes_capacite

conn = initialiser_base("donnees.db", recreer=True)
site_id, zones, lundi = generer_jeu_complet(conn)
generer_previsions_ressources(conn, site_id, zones, horizon_jours=14)
plan_id, lignes = elaborer_plan_charge(conn, site_id, zones, lundi)
generer_alertes_capacite(conn, site_id, lignes)
print(lignes[lignes["zone"] == "Réception"])
```

## Prochaine étape logique

Construire l'écran Tableau de bord (UC22) en Tkinter branché sur ces
services — c'est l'écran qui rend le scénario visible sans code.
