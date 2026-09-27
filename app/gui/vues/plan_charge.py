import tkinter as tk
from tkinter import ttk, messagebox
from app.services.planification import generer_previsions_ressources, elaborer_plan_charge
from app.services.alertes import generer_alertes_capacite
from app.gui.style import couleur_statut


class EcranPlanCharge(ttk.Frame):
    def __init__(self, parent, conn, contexte):
        super().__init__(parent, style="Fond.TFrame", padding=20)
        self.conn = conn
        self.contexte = contexte
        self._construire()
        self._afficher(self.contexte.get("lignes_plan"))

    def _construire(self):
        entete = ttk.Frame(self, style="Fond.TFrame")
        entete.pack(fill="x")
        ttk.Label(entete, text="Plan de charge — semaine de démonstration", style="Titre.TLabel").pack(side="left")
        ttk.Button(entete, text="Régénérer les prévisions et le plan",
                   command=self.regenerer).pack(side="right")

        ttk.Label(self, text="Cases en rouge : besoin d'effectif ou d'équipements supérieur à la capacité.",
                  style="Petite.TLabel").pack(anchor="w", pady=(5, 10))

        colonnes = ("zone", "date", "besoin_effectif", "capacite_effectif",
                    "besoin_equipements", "capacite_equipements", "adequation_pct")
        libelles = ["Zone", "Date", "Besoin effectif", "Capacité effectif",
                    "Besoin équip.", "Capacité équip.", "Adéquation %"]
        self.arbre = ttk.Treeview(self, columns=colonnes, show="headings", height=20)
        for c, l in zip(colonnes, libelles):
            self.arbre.heading(c, text=l)
            self.arbre.column(c, width=130, anchor="center")
        self.arbre.column("zone", width=140, anchor="w")
        self.arbre.pack(fill="both", expand=True)
        self.arbre.tag_configure("depassement", background="#fdecea", foreground=couleur_statut("rouge"))
        self.arbre.tag_configure("normal", background="white")

    def regenerer(self):
        site_id, zones, lundi = self.contexte["site_id"], self.contexte["zones"], self.contexte["lundi"]
        generer_previsions_ressources(self.conn, site_id, zones, horizon_jours=14)
        plan_id, lignes = elaborer_plan_charge(self.conn, site_id, zones, lundi)
        generer_alertes_capacite(self.conn, site_id, lignes)
        self.contexte["lignes_plan"] = lignes
        self._afficher(lignes)
        messagebox.showinfo("Plan de charge", "Prévisions et plan de charge régénérés.")

    def _afficher(self, lignes):
        for r in self.arbre.get_children():
            self.arbre.delete(r)
        if lignes is None or lignes.empty:
            return
        for _, l in lignes.sort_values(["zone", "date"]).iterrows():
            tag = "depassement" if l["depassement"] else "normal"
            self.arbre.insert("", "end", tags=(tag,), values=(
                l["zone"], l["date"], l["besoin_effectif"], l["capacite_effectif"],
                l["besoin_equipements"], l["capacite_equipements"], f"{l['adequation_pct']:.1f}"))
