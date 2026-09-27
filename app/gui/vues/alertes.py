import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from app.services.alertes import traiter_alerte
from app.gui.style import couleur_statut


class EcranAlertes(ttk.Frame):
    def __init__(self, parent, conn, contexte):
        super().__init__(parent, style="Fond.TFrame", padding=20)
        self.conn = conn
        self.contexte = contexte
        self._construire()
        self.actualiser()

    def _construire(self):
        entete = ttk.Frame(self, style="Fond.TFrame")
        entete.pack(fill="x")
        ttk.Label(entete, text="Alertes", style="Titre.TLabel").pack(side="left")
        ttk.Button(entete, text="Actualiser", command=self.actualiser).pack(side="right")

        colonnes = ("id", "type", "niveau", "statut", "message", "date")
        self.arbre = ttk.Treeview(self, columns=colonnes, show="headings", height=18)
        for c, l, w in [("id", "ID", 40), ("type", "Type", 140), ("niveau", "Niveau", 70),
                        ("statut", "Statut", 90), ("message", "Message", 480), ("date", "Concernée", 100)]:
            self.arbre.heading(c, text=l)
            self.arbre.column(c, width=w, anchor="w")
        self.arbre.pack(fill="both", expand=True, pady=(10, 10))
        self.arbre.tag_configure("rouge", foreground=couleur_statut("rouge"))
        self.arbre.tag_configure("orange", foreground=couleur_statut("orange"))

        boutons = ttk.Frame(self, style="Fond.TFrame")
        boutons.pack(fill="x")
        ttk.Button(boutons, text="Prendre en charge", command=self.prendre_en_charge).pack(side="left", padx=(0, 10))
        ttk.Button(boutons, text="Clôturer l'alerte…", command=self.cloturer).pack(side="left")

    def actualiser(self):
        for r in self.arbre.get_children():
            self.arbre.delete(r)
        rows = self.conn.execute(
            "SELECT id, type, niveau, statut, message, date_concernee FROM alertes WHERE site_id=? "
            "ORDER BY CASE statut WHEN 'ouverte' THEN 0 WHEN 'en_cours' THEN 1 ELSE 2 END, "
            "CASE niveau WHEN 'rouge' THEN 0 ELSE 1 END", (self.contexte["site_id"],)).fetchall()
        for a in rows:
            self.arbre.insert("", "end", iid=a["id"], tags=(a["niveau"],),
                               values=(a["id"], a["type"], a["niveau"], a["statut"], a["message"], a["date_concernee"] or ""))

    def _selection(self):
        sel = self.arbre.selection()
        if not sel:
            messagebox.showwarning("Alertes", "Sélectionnez une alerte.")
            return None
        return int(sel[0])

    def prendre_en_charge(self):
        alerte_id = self._selection()
        if alerte_id is None:
            return
        traiter_alerte(self.conn, alerte_id, nouveau_statut="en_cours")
        self.actualiser()

    def cloturer(self):
        alerte_id = self._selection()
        if alerte_id is None:
            return
        action = simpledialog.askstring("Clôturer l'alerte", "Action menée (obligatoire) :", parent=self)
        if not action:
            messagebox.showwarning("Alertes", "L'action menée est obligatoire pour clôturer une alerte.")
            return
        traiter_alerte(self.conn, alerte_id, action=action, nouveau_statut="resolue")
        self.actualiser()
