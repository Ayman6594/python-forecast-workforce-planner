import tkinter as tk
from tkinter import ttk
from app.services.auth import authentifier
from app.gui.style import POLICE_TITRE, POLICE_NORMALE, COULEUR_ROUGE, COULEUR_FOND


class EcranConnexion(ttk.Frame):
    def __init__(self, parent, conn, au_succes):
        super().__init__(parent, style="Fond.TFrame", padding=40)
        self.conn = conn
        self.au_succes = au_succes

        carte = ttk.Frame(self, style="Fond.TFrame")
        carte.place(relx=0.5, rely=0.5, anchor="center")

        ttk.Label(carte, text="Planification RH et équipements — 2.3.3", style="Titre.TLabel").grid(
            row=0, column=0, columnspan=2, pady=(0, 20))

        ttk.Label(carte, text="Identifiant", style="Normal.TLabel").grid(row=1, column=0, sticky="w", pady=5)
        self.champ_identifiant = ttk.Entry(carte, width=28, font=POLICE_NORMALE)
        self.champ_identifiant.grid(row=1, column=1, pady=5)

        ttk.Label(carte, text="Mot de passe", style="Normal.TLabel").grid(row=2, column=0, sticky="w", pady=5)
        self.champ_mot_de_passe = ttk.Entry(carte, width=28, show="•", font=POLICE_NORMALE)
        self.champ_mot_de_passe.grid(row=2, column=1, pady=5)
        self.champ_mot_de_passe.bind("<Return>", lambda e: self.se_connecter())

        self.label_erreur = ttk.Label(carte, text="", style="Normal.TLabel", foreground=COULEUR_ROUGE)
        self.label_erreur.grid(row=3, column=0, columnspan=2, pady=(5, 10))

        boutons = ttk.Frame(carte, style="Fond.TFrame")
        boutons.grid(row=4, column=0, columnspan=2)
        ttk.Button(boutons, text="Se connecter", command=self.se_connecter).pack(side="left", padx=5)
        ttk.Button(boutons, text="Quitter", command=parent.quit).pack(side="left", padx=5)

        ttk.Label(carte, text="Comptes de démonstration : admin / planif / resp / direction — mot de passe demo1234",
                  style="Petite.TLabel").grid(row=5, column=0, columnspan=2, pady=(15, 0))

        self.champ_identifiant.focus_set()

    def se_connecter(self):
        identifiant = self.champ_identifiant.get().strip()
        mot_de_passe = self.champ_mot_de_passe.get()
        succes, message, utilisateur = authentifier(self.conn, identifiant, mot_de_passe)
        if succes:
            self.au_succes(utilisateur)
        else:
            self.label_erreur.config(text=message)
