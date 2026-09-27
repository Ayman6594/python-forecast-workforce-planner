# 2.3.3: Ressources humaines et équipements

Application de prévision et de planification des ressources (effectif +
équipements) pour un sous-processus logistique, basée sur la comparaison de
deux modèles de machine learning (régression linéaire vs réseau de
neurones). Backend Python testé + interface graphique Tkinter.

## Démo
  
  https://github.com/user-attachments/assets/e478f7fd-dd9b-44db-adc7-12b22ef1b390


## Le scénario

Un pic de volume de +55 % est prévu jeudi sur la zone Réception, en même
temps que 2 chariots élévateurs sont indisponibles pour maintenance. Le
planning du personnel, lui, reste identique à celui de la semaine
précédente. L'application doit :

1. **Prévoir** les heures et équipements nécessaires à partir du volume
   prévu (deux modèles ML comparés : régression linéaire et réseau de
   neurones).
2. **Comparer** ce besoin à la capacité réellement planifiée.
3. **Alerter** avant que le jeudi n'arrive si un écart apparaît.

## Ce qui fonctionne (12 tests automatisés, tous verts)

- **Base de données** (`app/bd/`) : schéma complet (sites, zones,
  équipements, historique, prévisions, modèles, plans de charge, KPI,
  alertes, utilisateurs).
- **Génération de données de démonstration** (`app/demo/generateur.py`) :
  18 mois d'historique réaliste + la semaine de démonstration décrite
  ci-dessus.
- **Modèles de prévision** (`app/ml/entrainement.py`) : régression linéaire
  et réseau de neurones (scikit-learn), découpage chronologique 80/20,
  intervalle de confiance par quantiles des résidus.
- **Prévision de ressources et plan de charge** (`app/services/planification.py`) :
  besoin vs capacité par zone et par jour, avec drapeau de dépassement.
- **KPI** (`app/services/kpi.py`) : 4 règles de statut (baisse, hausse,
  plage, information), testées unitairement.
- **Alertes** (`app/services/alertes.py`) : sous-effectif, sureffectif,
  pénurie d'équipements, avec déduplication et clôture obligatoirement
  justifiée.
- **Comparaison réel/prévu et détection de dérive** (`app/services/comparaison.py`) :
  MAE/RMSE/MAPE/biais/taux de victoire par méthode.
- **Authentification** (`app/services/auth.py`) : hachage PBKDF2,
  verrouillage après 5 échecs / 15 min.
- **Interface graphique Tkinter** (`app/gui/`) : 4 écrans — Connexion,
  Tableau de bord, Plan de charge, Alertes — connectés en direct aux
  services ci-dessus (le bouton « Régénérer » relance réellement
  l'entraînement ML et le calcul du plan).
- **Test d'acceptation de bout en bout** (`tests/test_scenario_demo.py`)
  qui rejoue le scénario ci-dessus et vérifie les 5 comportements attendus.

## Ce qui manque encore

- Écrans dédiés pour Données, Prévisions détaillées, Comparaison, KPI,
  Rapports, Modèles, Administration (les services existent et sont
  testés, l'écran manque).
- Export de rapports (PDF/Excel), tâches planifiées automatiques.
- Gestion des utilisateurs en interface graphique (4 comptes de démo créés
  directement par le générateur).
- PostgreSQL en remplacement de SQLite (aucun serveur PostgreSQL n'était
  disponible pendant le développement ; la logique métier est écrite
  indépendamment du moteur, la migration du schéma est mécanique).

## Installation

\`\`\`bash
pip install -r requirements.txt
\`\`\`

## Lancer l'application graphique

\`\`\`bash
python -m app
\`\`\`

Comptes de démonstration (mot de passe `demo1234`) : `admin`, `planif`,
`resp`, `direction`. Le rôle change les écrans visibles dans le menu de
gauche (`direction` ne voit que le tableau de bord).

Au premier lancement, `donnees.db` est créé et peuplé automatiquement.
Supprimez ce fichier pour régénérer les données depuis zéro.

## Lancer les tests

\`\`\`bash
python -m pytest tests/ -v
\`\`\`

## Rejouer le scénario en ligne de commande

\`\`\`python
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
\`\`\`

## Structure

\`\`\`
app/
  bd/          schéma et connexion SQLite
  demo/        générateur de données de démonstration
  ml/          entraînement et prédiction (RL + RN)
  services/    logique métier (auth, planification, alertes, KPI, comparaison)
  gui/         interface Tkinter
tests/         suite pytest (12 tests)
\`\`\`
