"""Règles de statut des KPI (UC17). Sens : baisse / hausse / plage / information."""


def statut_baisse(valeur, seuil_orange, seuil_rouge):
    if valeur <= seuil_orange:
        return "vert"
    if valeur <= seuil_rouge:
        return "orange"
    return "rouge"


def statut_hausse(valeur, seuil_orange, seuil_rouge):
    if valeur >= seuil_orange:
        return "vert"
    if valeur >= seuil_rouge:
        return "orange"
    return "rouge"


def statut_plage(valeur, valeur_min, valeur_max, marge):
    if valeur_min <= valeur <= valeur_max:
        return "vert"
    ecart = valeur_min - valeur if valeur < valeur_min else valeur - valeur_max
    if ecart <= marge:
        return "orange"
    return "rouge"


def evaluer_statut(sens, valeur, **seuils):
    if valeur is None:
        return None
    if sens == "information":
        return None
    if sens == "baisse":
        return statut_baisse(valeur, seuils["seuil_orange"], seuils["seuil_rouge"])
    if sens == "hausse":
        return statut_hausse(valeur, seuils["seuil_orange"], seuils["seuil_rouge"])
    if sens == "plage":
        return statut_plage(valeur, seuils["valeur_min"], seuils["valeur_max"], seuils["marge"])
    raise ValueError(f"Sens inconnu : {sens}")


def adequation(heures_planifiees, heures_necessaires_reelles):
    if heures_necessaires_reelles == 0:
        return None
    return heures_planifiees / heures_necessaires_reelles * 100


def taux(numerateur, denominateur):
    if denominateur == 0:
        return None
    return numerateur / denominateur * 100
