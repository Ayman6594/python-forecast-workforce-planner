"""Feuille de style unique pour toute l'application (ttk)."""
import tkinter as tk
from tkinter import ttk

COULEUR_FOND = "#f4f6f8"
COULEUR_BANDEAU = "#1f2a44"
COULEUR_BANDEAU_TEXTE = "#ffffff"
COULEUR_ACCENT = "#2f6fed"
COULEUR_VERT = "#1e8e3e"
COULEUR_ORANGE = "#e37400"
COULEUR_ROUGE = "#d93025"
COULEUR_GRIS = "#5f6368"

POLICE_TITRE = ("Segoe UI", 16, "bold")
POLICE_SOUS_TITRE = ("Segoe UI", 11, "bold")
POLICE_NORMALE = ("Segoe UI", 10)
POLICE_PETITE = ("Segoe UI", 9)


def appliquer_style(racine: tk.Tk):
    racine.configure(bg=COULEUR_FOND)
    style = ttk.Style(racine)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    style.configure("Fond.TFrame", background=COULEUR_FOND)
    style.configure("Bandeau.TFrame", background=COULEUR_BANDEAU)
    style.configure("Bandeau.TLabel", background=COULEUR_BANDEAU, foreground=COULEUR_BANDEAU_TEXTE,
                     font=POLICE_SOUS_TITRE)
    style.configure("Titre.TLabel", background=COULEUR_FOND, font=POLICE_TITRE)
    style.configure("SousTitre.TLabel", background=COULEUR_FOND, font=POLICE_SOUS_TITRE)
    style.configure("Normal.TLabel", background=COULEUR_FOND, font=POLICE_NORMALE)
    style.configure("Petite.TLabel", background=COULEUR_FOND, font=POLICE_PETITE, foreground=COULEUR_GRIS)

    style.configure("Accent.TButton", font=POLICE_NORMALE)
    style.map("Accent.TButton", background=[("!disabled", COULEUR_ACCENT)])

    style.configure("Nav.TButton", font=POLICE_NORMALE, anchor="w")
    style.configure("NavActif.TButton", font=("Segoe UI", 10, "bold"), anchor="w")

    style.configure("Treeview", font=POLICE_NORMALE, rowheight=24)
    style.configure("Treeview.Heading", font=POLICE_SOUS_TITRE)
    return style


def couleur_statut(statut: str) -> str:
    return {"vert": COULEUR_VERT, "orange": COULEUR_ORANGE, "rouge": COULEUR_ROUGE}.get(statut, COULEUR_GRIS)
