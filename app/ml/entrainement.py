"""Entraînement et prédiction des modèles RL et RN (UC07-UC11)."""
import math
import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression
from sklearn.neural_network import MLPRegressor

GRAINE = 42


def construire_variables(df: pd.DataFrame, colonne_volume: str) -> pd.DataFrame:
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    df["jour_semaine"] = df["date"].dt.weekday
    for j in range(7):
        df[f"jour_{j}"] = (df["jour_semaine"] == j).astype(int)
    df["mois_sin"] = np.sin(2 * math.pi * df["date"].dt.month / 12)
    df["mois_cos"] = np.cos(2 * math.pi * df["date"].dt.month / 12)
    df["volume_moy_7j"] = df[colonne_volume].rolling(7, min_periods=1).mean().shift(1).fillna(df[colonne_volume].mean())
    return df


COLONNES_X = ["volume", "mois_sin", "mois_cos", "volume_moy_7j", "indicateur_pic"] + [f"jour_{j}" for j in range(7)]


def _decoupage_chronologique(df, part_test=0.2):
    n_test = max(1, int(len(df) * part_test))
    return df.iloc[: len(df) - n_test], df.iloc[len(df) - n_test :]


def _construire_matrice(df, colonne_volume):
    d = df.copy()
    d["volume"] = d[colonne_volume]
    if "indicateur_pic" not in d.columns:
        d["indicateur_pic"] = 0
    return d[COLONNES_X]


def entrainer(historique: pd.DataFrame, colonne_volume: str, colonne_cible: str):
    """Entraîne RL et RN sur historique, découpage chronologique 80/20.

    Retourne un dict {methode: {"pipeline":..., "metriques":..., "quantiles_residus": (q10,q90)}}
    """
    df = construire_variables(historique, colonne_volume)
    entrainement, test = _decoupage_chronologique(df)
    if len(entrainement) < 30:
        raise ValueError("Historique insuffisant (moins de 90 jours recommandés) pour un entraînement fiable.")

    X_train, y_train = _construire_matrice(entrainement, colonne_volume), entrainement[colonne_cible]
    X_test, y_test = _construire_matrice(test, colonne_volume), test[colonne_cible]

    resultats = {}
    modeles = {
        "regression_lineaire": Pipeline([("scaler", StandardScaler()), ("reg", LinearRegression())]),
        "reseau_neurones": Pipeline([("scaler", StandardScaler()), ("reg", MLPRegressor(
            hidden_layer_sizes=(32, 16), activation="relu", early_stopping=True,
            max_iter=2000, random_state=GRAINE))]),
    }
    for methode, pipeline in modeles.items():
        pipeline.fit(X_train, y_train)
        preds = pipeline.predict(X_test)
        residus_test = y_test.values - preds
        mae = float(np.mean(np.abs(residus_test)))
        rmse = float(np.sqrt(np.mean(residus_test ** 2)))
        reel_non_nul = y_test.values != 0
        mape = float(np.mean(np.abs(residus_test[reel_non_nul]) / y_test.values[reel_non_nul]) * 100) if reel_non_nul.any() else None
        biais = float(np.sum(preds - y_test.values) / np.sum(y_test.values) * 100) if y_test.sum() != 0 else None
        q10, q90 = np.quantile(residus_test, [0.10, 0.90])
        couverture = float(np.mean((residus_test >= q10) & (residus_test <= q90)) * 100)
        resultats[methode] = {
            "pipeline": pipeline,
            "metriques": {"mae": mae, "rmse": rmse, "mape": mape, "biais": biais, "couverture_ic": couverture},
            "quantiles_residus": (float(q10), float(q90)),
        }
    return resultats


def predire(pipeline, quantiles_residus, previsions_volume: pd.DataFrame, colonne_volume="volume_prevu"):
    df = construire_variables(previsions_volume, colonne_volume)
    X = _construire_matrice(df, colonne_volume)
    points = pipeline.predict(X)
    q10, q90 = quantiles_residus
    return pd.DataFrame({
        "date": df["date"].dt.date,
        "prediction": np.maximum(points, 0),
        "ic_bas": np.maximum(points + q10, 0),
        "ic_haut": np.maximum(points + q90, 0),
    })


def heures_vers_effectif(heures, duree_poste):
    return max(0, math.ceil(heures / duree_poste)) if heures > 0 else 0


def vers_equipements(valeur):
    return max(0, math.ceil(valeur)) if valeur > 0 else 0
