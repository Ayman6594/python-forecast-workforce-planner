import tkinter as tk
from tkinter import ttk
from datetime import date
from app.gui.style import COULEUR_FOND, couleur_statut


class EcranTableauBord(ttk.Frame):
    def __init__(self, parent, conn, contexte):
        super().__init__(parent, style="Fond.TFrame", padding=20)
        self.conn = conn
        self.contexte = contexte
        self._construire()
        self.actualiser()

    def _construire(self):
        ttk.Label(self, text="Tableau de bord", style="Titre.TLabel").pack(anchor="w")
        ttk.Label(self, text="Plateforme Casablanca — semaine de démonstration", style="Petite.TLabel").pack(
            anchor="w", pady=(0, 15))

        self.cadre_tuiles = ttk.Frame(self, style="Fond.TFrame")
        self.cadre_tuiles.pack(fill="x", pady=(0, 15))

        ttk.Label(self, text="Alertes ouvertes", style="SousTitre.TLabel").pack(anchor="w", pady=(10, 5))
        colonnes = ("type", "niveau", "message", "date")
        self.arbre_alertes = ttk.Treeview(self, columns=colonnes, show="headings", height=8)
        for c, l, w in [("type", "Type", 140), ("niveau", "Niveau", 80),
                        ("message", "Message", 520), ("date", "Concernée", 100)]:
            self.arbre_alertes.heading(c, text=l)
            self.arbre_alertes.column(c, width=w, anchor="w")
        self.arbre_alertes.pack(fill="both", expand=True)

        ttk.Button(self, text="Actualiser", command=self.actualiser).pack(anchor="e", pady=10)

    def _tuile(self, parent, titre, valeur, couleur="#1f2a44"):
        cadre = tk.Frame(parent, bg="white", highlightbackground="#dadce0", highlightthickness=1)
        tk.Label(cadre, text=titre, bg="white", fg="#5f6368", font=("Segoe UI", 9)).pack(anchor="w", padx=12, pady=(10, 0))
        tk.Label(cadre, text=str(valeur), bg="white", fg=couleur, font=("Segoe UI", 20, "bold")).pack(
            anchor="w", padx=12, pady=(0, 10))
        return cadre

    def actualiser(self):
        for w in self.cadre_tuiles.winfo_children():
            w.destroy()
        for r in self.arbre_alertes.get_children():
            self.arbre_alertes.delete(r)

        site_id = self.contexte["site_id"]
        alertes = self.conn.execute(
            "SELECT type, niveau, message, date_concernee FROM alertes WHERE site_id=? AND statut!='resolue' "
            "ORDER BY CASE niveau WHEN 'rouge' THEN 0 ELSE 1 END, date_concernee", (site_id,)).fetchall()

        nb_rouge = sum(1 for a in alertes if a["niveau"] == "rouge")
        nb_orange = sum(1 for a in alertes if a["niveau"] == "orange")
        lignes = self.contexte.get("lignes_plan")
        nb_depassements = int(lignes["depassement"].sum()) if lignes is not None else 0

        self._tuile(self.cadre_tuiles, "Alertes rouges", nb_rouge, couleur_statut("rouge")).pack(
            side="left", padx=(0, 10), ipadx=10)
        self._tuile(self.cadre_tuiles, "Alertes oranges", nb_orange, couleur_statut("orange")).pack(
            side="left", padx=10, ipadx=10)
        self._tuile(self.cadre_tuiles, "Jours en dépassement (plan)", nb_depassements).pack(
            side="left", padx=10, ipadx=10)
        self._tuile(self.cadre_tuiles, "Semaine du", self.contexte["lundi"].strftime("%d/%m/%Y")).pack(
            side="left", padx=10, ipadx=10)

        for a in alertes:
            self.arbre_alertes.insert("", "end", values=(a["type"], a["niveau"], a["message"], a["date_concernee"] or ""),
                                       tags=(a["niveau"],))
        self.arbre_alertes.tag_configure("rouge", foreground=couleur_statut("rouge"))
        self.arbre_alertes.tag_configure("orange", foreground=couleur_statut("orange"))
