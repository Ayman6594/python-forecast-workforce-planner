import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date

from app.bd.connexion import initialiser_base
from app.demo.generateur import generer_jeu_complet
from app.services.planification import generer_previsions_ressources, elaborer_plan_charge
from app.services.alertes import generer_alertes_capacite
from app.gui.style import appliquer_style, POLICE_NORMALE
from app.gui.vues.connexion import EcranConnexion
from app.gui.vues.tableau_bord import EcranTableauBord
from app.gui.vues.plan_charge import EcranPlanCharge
from app.gui.vues.alertes import EcranAlertes

TEXTE_A_PROPOS = """Un lundi matin, sur une plateforme logistique. La prévision de la demande
annonce un pic de 40 % pour jeudi, porté par une campagne promotionnelle. Pourtant,
le planning des équipes est le même que la semaine précédente, et deux chariots
élévateurs sont en maintenance.

Jeudi arrive. Les camions attendent à quai faute de caristes. Les commandes
s'accumulent en préparation. Les heures supplémentaires explosent et des
intérimaires sont appelés en urgence, sans formation. Les engagements de
service ne sont pas tenus.

Le sous-processus 2.3.3 « Ressources humaines et équipements » (Prévision et
planification > Planification des capacités) répond à une question simple :
« Pour le volume prévu, de quoi aurai-je besoin, et quand ? » Il compare une
régression linéaire et un réseau de neurones pour prévoir les heures et les
équipements nécessaires, compare le plan à la capacité réelle, et déclenche
des alertes avant que le jeudi n'arrive.

Version de démonstration — noyau métier (base de données, prévision, plan de
charge, KPI, alertes) avec une interface graphique réduite à 4 écrans."""


ECRANS_PAR_ROLE = {
    "planificateur": [("Tableau de bord", "dashboard"), ("Plan de charge", "plan"), ("Alertes", "alertes")],
    "responsable": [("Tableau de bord", "dashboard"), ("Plan de charge", "plan"), ("Alertes", "alertes")],
    "direction": [("Tableau de bord", "dashboard")],
    "administrateur": [("Tableau de bord", "dashboard"), ("Plan de charge", "plan"), ("Alertes", "alertes")],
}


class FenetrePrincipale(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Planification RH et équipements — 2.3.3")
        self.geometry("1366x768")
        self.minsize(1024, 640)
        appliquer_style(self)

        self.conn = initialiser_base("donnees.db")
        self._assurer_donnees_demo()

        self.utilisateur = None
        self.contexte = {}
        self.cadre_courant = None
        self._afficher_connexion()

    def _assurer_donnees_demo(self):
        deja = self.conn.execute("SELECT COUNT(*) FROM sites").fetchone()[0]
        if deja:
            return
        site_id, zones, lundi = generer_jeu_complet(self.conn)
        generer_previsions_ressources(self.conn, site_id, zones, horizon_jours=14)
        plan_id, lignes = elaborer_plan_charge(self.conn, site_id, zones, lundi)
        generer_alertes_capacite(self.conn, site_id, lignes)
        self.contexte = {"site_id": site_id, "zones": zones, "lundi": lundi,
                          "plan_id": plan_id, "lignes_plan": lignes}

    def _charger_contexte_existant(self):
        if self.contexte:
            return
        site = self.conn.execute("SELECT id FROM sites LIMIT 1").fetchone()
        zones_rows = self.conn.execute("SELECT id, nom FROM zones WHERE site_id=?", (site["id"],)).fetchall()
        zones = {z["nom"]: z["id"] for z in zones_rows}
        lundi_row = self.conn.execute("SELECT semaine FROM plans_charge WHERE site_id=? ORDER BY semaine LIMIT 1",
                                       (site["id"],)).fetchone()
        lundi = date.fromisoformat(lundi_row["semaine"]) if lundi_row else date.today()
        self.contexte = {"site_id": site["id"], "zones": zones, "lundi": lundi, "lignes_plan": None}

    def _afficher_connexion(self):
        if self.cadre_courant:
            self.cadre_courant.destroy()
        self.cadre_courant = EcranConnexion(self, self.conn, au_succes=self._apres_connexion)
        self.cadre_courant.pack(fill="both", expand=True)

    def _apres_connexion(self, utilisateur):
        self.utilisateur = utilisateur
        self._charger_contexte_existant()
        self._construire_coquille()

    def _construire_coquille(self):
        self.cadre_courant.destroy()
        self.cadre_courant = ttk.Frame(self, style="Fond.TFrame")
        self.cadre_courant.pack(fill="both", expand=True)

        bandeau = ttk.Frame(self.cadre_courant, style="Bandeau.TFrame", padding=10)
        bandeau.pack(fill="x")
        ttk.Label(bandeau, text="Planification RH et équipements — 2.3.3", style="Bandeau.TLabel").pack(side="left")
        cadre_droite = ttk.Frame(bandeau, style="Bandeau.TFrame")
        cadre_droite.pack(side="right")
        ttk.Label(cadre_droite, text=f"{self.utilisateur['prenom']} {self.utilisateur['nom']} ({self.utilisateur['role']})",
                  style="Bandeau.TLabel").pack(side="left", padx=10)
        ttk.Button(cadre_droite, text="Se déconnecter", command=self._deconnecter).pack(side="left")
        ttk.Button(cadre_droite, text="À propos", command=self._afficher_a_propos).pack(side="left", padx=(10, 0))

        corps = ttk.Frame(self.cadre_courant, style="Fond.TFrame")
        corps.pack(fill="both", expand=True)

        menu = ttk.Frame(corps, style="Fond.TFrame", padding=10, width=200)
        menu.pack(side="left", fill="y")
        self.zone_contenu = ttk.Frame(corps, style="Fond.TFrame", padding=15)
        self.zone_contenu.pack(side="left", fill="both", expand=True)

        for libelle, cle in ECRANS_PAR_ROLE.get(self.utilisateur["role"], []):
            ttk.Button(menu, text=libelle, style="Nav.TButton",
                       command=lambda c=cle: self._afficher_ecran(c)).pack(fill="x", pady=3)

        self._afficher_ecran(ECRANS_PAR_ROLE.get(self.utilisateur["role"], [(None, "dashboard")])[0][1])

    def _afficher_ecran(self, cle):
        for w in self.zone_contenu.winfo_children():
            w.destroy()
        if cle == "dashboard":
            EcranTableauBord(self.zone_contenu, self.conn, self.contexte).pack(fill="both", expand=True)
        elif cle == "plan":
            EcranPlanCharge(self.zone_contenu, self.conn, self.contexte).pack(fill="both", expand=True)
        elif cle == "alertes":
            EcranAlertes(self.zone_contenu, self.conn, self.contexte).pack(fill="both", expand=True)

    def _afficher_a_propos(self):
        fenetre = tk.Toplevel(self)
        fenetre.title("À propos")
        fenetre.geometry("620x460")
        texte = tk.Text(fenetre, wrap="word", font=POLICE_NORMALE, padx=15, pady=15)
        texte.insert("1.0", TEXTE_A_PROPOS)
        texte.config(state="disabled")
        texte.pack(fill="both", expand=True)
        ttk.Button(fenetre, text="Fermer", command=fenetre.destroy).pack(pady=10)

    def _deconnecter(self):
        self.utilisateur = None
        self._afficher_connexion()


def lancer():
    app = FenetrePrincipale()
    app.mainloop()
