import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.kpi import evaluer_statut, adequation, taux


def test_baisse():
    assert evaluer_statut("baisse", 5, seuil_orange=10, seuil_rouge=15) == "vert"
    assert evaluer_statut("baisse", 12, seuil_orange=10, seuil_rouge=15) == "orange"
    assert evaluer_statut("baisse", 20, seuil_orange=10, seuil_rouge=15) == "rouge"


def test_hausse():
    assert evaluer_statut("hausse", 96, seuil_orange=95, seuil_rouge=90) == "vert"
    assert evaluer_statut("hausse", 92, seuil_orange=95, seuil_rouge=90) == "orange"
    assert evaluer_statut("hausse", 80, seuil_orange=95, seuil_rouge=90) == "rouge"


def test_plage():
    assert evaluer_statut("plage", 100, valeur_min=95, valeur_max=105, marge=5) == "vert"
    assert evaluer_statut("plage", 108, valeur_min=95, valeur_max=105, marge=5) == "orange"
    assert evaluer_statut("plage", 115, valeur_min=95, valeur_max=105, marge=5) == "rouge"
    assert evaluer_statut("plage", 92, valeur_min=95, valeur_max=105, marge=5) == "orange"
    assert evaluer_statut("plage", 85, valeur_min=95, valeur_max=105, marge=5) == "rouge"


def test_information_sans_statut():
    assert evaluer_statut("information", 42) is None


def test_valeur_none():
    assert evaluer_statut("baisse", None, seuil_orange=10, seuil_rouge=15) is None


def test_adequation_division_par_zero():
    assert adequation(100, 0) is None
    assert adequation(95, 100) == 95.0


def test_taux():
    assert taux(5, 20) == 25.0
    assert taux(5, 0) is None
