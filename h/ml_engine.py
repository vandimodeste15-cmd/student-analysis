"""
ML Analysis Engine
==================
Handles:
  A. Simple Linear Regression  – predict grade from study hours
  B. Multiple Linear Regression – predict grade from all features
  C. PCA Dimensionality Reduction
  D. Supervised Classification  – High / Average / Low Performer
  E. K-Means Clustering

All chart functions return a base64-encoded PNG string ready for <img> tags.
"""

import io
import base64
import warnings
import logging
from typing import Optional

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")          # non-interactive backend (server-safe)
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from sklearn.neighbors import KNeighborsClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, silhouette_score

warnings.filterwarnings("ignore")
logger = logging.getLogger(__name__)

# ── Seaborn / matplotlib styling ────────────────────────────────────────────
sns.set_theme(style="darkgrid", palette="muted")
FEATURE_COLS = ["study_hours", "sleep_hours", "social_media_hours", "attendance_rate"]
TARGET_COL   = "previous_grade"
MIN_ROWS     = 5          # minimum rows needed for any analysis


# ── Helpers ─────────────────────────────────────────────────────────────────

def _fig_to_b64(fig) -> str:
    """Convert a matplotlib Figure to a base64-encoded PNG string."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=110)
    buf.seek(0)
    encoded = base64.b64encode(buf.read()).decode("utf-8")
    plt.close(fig)
    return encoded


def _build_df(entries: list) -> Optional[pd.DataFrame]:
    """Convert a list of StudentEntry objects into a clean DataFrame."""
    if not entries:
        return None
    records = [e.to_dict() for e in entries]
    df = pd.DataFrame(records)

    numeric_cols = FEATURE_COLS + [TARGET_COL]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df.dropna(subset=numeric_cols, inplace=True)
    return df if len(df) >= MIN_ROWS else None


def _label_performance(grade: float) -> str:
    """Rule-based performance label from grade."""
    if grade >= 75:
        return "High Performer"
    elif grade >= 50:
        return "Average"
    return "Low Performer"


# ── A. Simple Linear Regression ─────────────────────────────────────────────

def simple_linear_regression(df: pd.DataFrame) -> dict:
    """
    Predict grade from study hours alone.
    Returns: model, chart_b64, equation string, r2 score.
    """
    result = {"available": False, "chart": None, "equation": "", "r2": None}
    try:
        X = df[["study_hours"]].values
        y = df[TARGET_COL].values

        model = LinearRegression()
        model.fit(X, y)
        r2 = model.score(X, y)
        coef = model.coef_[0]
        intercept = model.intercept_

        # Scatter + regression line
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.scatter(X, y, color="#4c72b0", alpha=0.7, label="Actual")
        x_line = np.linspace(X.min(), X.max(), 100).reshape(-1, 1)
        ax.plot(x_line, model.predict(x_line), color="#dd8452", linewidth=2, label="Regression line")
        ax.set_xlabel("Study Hours per Day")
        ax.set_ylabel("Grade (%)")
        ax.set_title("Simple Linear Regression: Study Hours → Grade")
        ax.legend()
        fig.tight_layout()

        result.update({
            "available": True,
            "chart": _fig_to_b64(fig),
            "equation": f"Grade = {coef:.2f} × StudyHours + {intercept:.2f}",
            "r2": round(r2, 3),
            "model": model,
        })
    except Exception as exc:
        logger.warning("SLR failed: %s", exc)
    return result


# ── B. Multiple Linear Regression ───────────────────────────────────────────

def multiple_linear_regression(df: pd.DataFrame) -> dict:
    """
    Predict grade from all four lifestyle features.
    Returns: model, chart (coefficients bar), equation dict, r2.
    """
    result = {"available": False, "chart": None, "coefficients": {}, "r2": None}
    try:
        X = df[FEATURE_COLS].values
        y = df[TARGET_COL].values

        model = LinearRegression()
        model.fit(X, y)
        r2 = model.score(X, y)

        coef_dict = dict(zip(FEATURE_COLS, model.coef_))

        # Bar chart of coefficients
        fig, ax = plt.subplots(figsize=(7, 4))
        colors = ["#4c72b0" if v >= 0 else "#c44e52" for v in coef_dict.values()]
        ax.barh(list(coef_dict.keys()), list(coef_dict.values()), color=colors)
        ax.axvline(0, color="black", linewidth=0.8)
        ax.set_xlabel("Coefficient value")
        ax.set_title("Multiple Linear Regression: Feature Coefficients")
        fig.tight_layout()

        result.update({
            "available": True,
            "chart": _fig_to_b64(fig),
            "coefficients": {k: round(v, 3) for k, v in coef_dict.items()},
            "intercept": round(float(model.intercept_), 3),
            "r2": round(r2, 3),
            "model": model,
        })
    except Exception as exc:
        logger.warning("MLR failed: %s", exc)
    return result


def predict_grade(study_hours: float, sleep_hours: float,
                  social_media: float, attendance: float,
                  mlr_model) -> Optional[float]:
    """Use the fitted MLR model to predict a grade for one student."""
    try:
        X = np.array([[study_hours, sleep_hours, social_media, attendance]])
        return float(mlr_model.predict(X)[0])
    except Exception:
        return None


# ── C. PCA Dimensionality Reduction ─────────────────────────────────────────

def pca_analysis(df: pd.DataFrame) -> dict:
    """
    Reduce 4 features to 2 principal components and plot.
    Returns: explained_variance, chart_b64.
    """
    result = {"available": False, "chart": None, "explained_variance": []}
    try:
        X = df[FEATURE_COLS].values
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        pca = PCA(n_components=2)
        X_pca = pca.fit_transform(X_scaled)
        ev = pca.explained_variance_ratio_

        # Color-code by performance label
        labels = df[TARGET_COL].apply(_label_performance)
        color_map = {"High Performer": "#2ecc71", "Average": "#f39c12", "Low Performer": "#e74c3c"}
        colors = labels.map(color_map).fillna("#7f8c8d")

        fig, axes = plt.subplots(1, 2, figsize=(12, 4))

        # 2-D scatter of PC1 vs PC2
        for label, grp in df.assign(label=labels).groupby("label"):
            idx = grp.index
            axes[0].scatter(X_pca[idx, 0], X_pca[idx, 1],
                            label=label, color=color_map.get(label, "#7f8c8d"), alpha=0.8)
        axes[0].set_xlabel(f"PC1 ({ev[0]*100:.1f}% var)")
        axes[0].set_ylabel(f"PC2 ({ev[1]*100:.1f}% var)")
        axes[0].set_title("PCA — Students in 2D Space")
        axes[0].legend(fontsize=8)

        # Scree-like bar for all 4 components
        pca_full = PCA(n_components=len(FEATURE_COLS))
        pca_full.fit(X_scaled)
        axes[1].bar(range(1, len(FEATURE_COLS)+1), pca_full.explained_variance_ratio_ * 100, color="#4c72b0")
        axes[1].set_xlabel("Principal Component")
        axes[1].set_ylabel("Explained Variance (%)")
        axes[1].set_title("Explained Variance per Component")

        fig.tight_layout()

        result.update({
            "available": True,
            "chart": _fig_to_b64(fig),
            "explained_variance": [round(v * 100, 2) for v in pca_full.explained_variance_ratio_],
        })
    except Exception as exc:
        logger.warning("PCA failed: %s", exc)
    return result


# ── D. Supervised Classification ────────────────────────────────────────────

def supervised_classification(df: pd.DataFrame) -> dict:
    """
    KNN classifier: High Performer / Average / Low Performer.
    Returns: chart (confusion-like distribution), accuracy, report.
    """
    result = {"available": False, "chart": None, "accuracy": None, "distribution": {}}
    try:
        df = df.copy()
        df["label"] = df[TARGET_COL].apply(_label_performance)

        # Need at least 2 classes
        if df["label"].nunique() < 2:
            return result

        X = df[FEATURE_COLS].values
        y = df["label"].values

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        # Distribution bar chart (always shown, even with small data)
        dist = df["label"].value_counts()
        fig, ax = plt.subplots(figsize=(7, 4))
        colors_bar = [{"High Performer": "#2ecc71", "Average": "#f39c12",
                        "Low Performer": "#e74c3c"}.get(l, "#7f8c8d") for l in dist.index]
        ax.bar(dist.index, dist.values, color=colors_bar)
        ax.set_title("Student Performance Distribution")
        ax.set_ylabel("Number of Students")
        for i, v in enumerate(dist.values):
            ax.text(i, v + 0.1, str(v), ha="center", fontweight="bold")
        fig.tight_layout()

        distribution_chart = _fig_to_b64(fig)
        distribution = dist.to_dict()

        # KNN only if enough samples for train/test split
        accuracy = None
        if len(df) >= 10:
            X_train, X_test, y_train, y_test = train_test_split(
                X_scaled, y, test_size=0.25, random_state=42, stratify=y
            )
            k = min(5, len(X_train))
            clf = KNeighborsClassifier(n_neighbors=k)
            clf.fit(X_train, y_train)
            accuracy = round(clf.score(X_test, y_test) * 100, 1)

        result.update({
            "available": True,
            "chart": distribution_chart,
            "accuracy": accuracy,
            "distribution": distribution,
        })
    except Exception as exc:
        logger.warning("Classification failed: %s", exc)
    return result


# ── E. Unsupervised K-Means Clustering ──────────────────────────────────────

def kmeans_clustering(df: pd.DataFrame, n_clusters: int = 3) -> dict:
    """
    Group students into n_clusters using K-Means.
    Returns: chart, cluster labels per row, silhouette score.
    """
    result = {"available": False, "chart": None, "silhouette": None, "cluster_labels": []}
    try:
        X = df[FEATURE_COLS].values
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        # Cap clusters to avoid degenerate case
        n_clusters = min(n_clusters, len(df) - 1)
        if n_clusters < 2:
            return result

        km = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        labels = km.fit_predict(X_scaled)

        sil = round(silhouette_score(X_scaled, labels), 3)

        # PCA for 2-D cluster visualization
        pca = PCA(n_components=2)
        X_pca = pca.fit_transform(X_scaled)

        cluster_colors = ["#4c72b0", "#dd8452", "#55a868", "#c44e52", "#8172b2"]

        fig, axes = plt.subplots(1, 2, figsize=(12, 4))

        # Cluster scatter
        for c in range(n_clusters):
            mask = labels == c
            axes[0].scatter(X_pca[mask, 0], X_pca[mask, 1],
                            label=f"Cluster {c+1}",
                            color=cluster_colors[c % len(cluster_colors)],
                            alpha=0.8)
        # Plot centroids
        centroids_pca = pca.transform(km.cluster_centers_)
        axes[0].scatter(centroids_pca[:, 0], centroids_pca[:, 1],
                        c="black", marker="X", s=120, zorder=5, label="Centroids")
        axes[0].set_title(f"K-Means Clusters (k={n_clusters}) — PCA View")
        axes[0].set_xlabel("PC1"); axes[0].set_ylabel("PC2")
        axes[0].legend(fontsize=8)

        # Cluster sizes
        from collections import Counter
        sizes = Counter(labels)
        labels_names = [f"Cluster {c+1}" for c in range(n_clusters)]
        sizes_vals = [sizes[c] for c in range(n_clusters)]
        axes[1].pie(sizes_vals, labels=labels_names,
                    colors=cluster_colors[:n_clusters],
                    autopct="%1.0f%%", startangle=90)
        axes[1].set_title("Cluster Proportions")

        fig.tight_layout()

        result.update({
            "available": True,
            "chart": _fig_to_b64(fig),
            "silhouette": sil,
            "cluster_labels": labels.tolist(),
        })
    except Exception as exc:
        logger.warning("K-Means failed: %s", exc)
    return result


# ── F. Correlation Heatmap ───────────────────────────────────────────────────

def correlation_heatmap(df: pd.DataFrame) -> Optional[str]:
    """Return a seaborn correlation heatmap as base64 PNG."""
    try:
        corr = df[FEATURE_COLS + [TARGET_COL]].corr()
        fig, ax = plt.subplots(figsize=(7, 5))
        sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm",
                    linewidths=0.5, ax=ax, vmin=-1, vmax=1)
        ax.set_title("Feature Correlation Heatmap")
        fig.tight_layout()
        return _fig_to_b64(fig)
    except Exception as exc:
        logger.warning("Heatmap failed: %s", exc)
        return None


# ── G. Trends chart ─────────────────────────────────────────────────────────

def study_grade_trend(df: pd.DataFrame) -> Optional[str]:
    """
    Box-plot: grade distribution bucketed by study hours bins.
    Gives the insight 'students who study > X hrs perform better'.
    """
    try:
        df2 = df.copy()
        df2["study_bin"] = pd.cut(df2["study_hours"], bins=[0, 2, 4, 6, 8, 24],
                                  labels=["<2h", "2-4h", "4-6h", "6-8h", ">8h"])
        fig, ax = plt.subplots(figsize=(8, 4))
        df2.boxplot(column=TARGET_COL, by="study_bin", ax=ax,
                    boxprops=dict(color="#4c72b0"),
                    medianprops=dict(color="#dd8452", linewidth=2))
        ax.set_title("Grade Distribution by Daily Study Hours")
        ax.set_xlabel("Study Hours per Day")
        ax.set_ylabel("Grade (%)")
        plt.suptitle("")
        fig.tight_layout()
        return _fig_to_b64(fig)
    except Exception as exc:
        logger.warning("Trend chart failed: %s", exc)
        return None


# ── Master runner ────────────────────────────────────────────────────────────

def run_full_analysis(entries: list) -> dict:
    """
    Run all analyses on a list of StudentEntry objects.
    Returns a dict consumed by the dashboard template.
    """
    df = _build_df(entries)

    if df is None:
        return {
            "enough_data": False,
            "count": len(entries),
            "min_rows": MIN_ROWS,
        }

    # Run all modules
    slr  = simple_linear_regression(df)
    mlr  = multiple_linear_regression(df)
    pca  = pca_analysis(df)
    clf  = supervised_classification(df)
    km   = kmeans_clustering(df)
    heatmap  = correlation_heatmap(df)
    trend    = study_grade_trend(df)

    # Summary statistics
    stats = {
        "total": len(df),
        "avg_grade": round(df[TARGET_COL].mean(), 1),
        "avg_study": round(df["study_hours"].mean(), 1),
        "avg_sleep": round(df["sleep_hours"].mean(), 1),
        "avg_social": round(df["social_media_hours"].mean(), 1),
        "avg_attendance": round(df["attendance_rate"].mean(), 1),
    }

    # Insight: threshold where mean grade crosses 70
    insight_threshold = None
    for h in np.arange(1, 10, 0.5):
        subset = df[df["study_hours"] >= h]
        if len(subset) >= 3 and subset[TARGET_COL].mean() >= 70:
            insight_threshold = h
            break

    return {
        "enough_data": True,
        "stats": stats,
        "slr": slr,
        "mlr": mlr,
        "pca": pca,
        "classification": clf,
        "clustering": km,
        "heatmap": heatmap,
        "trend": trend,
        "insight_threshold": insight_threshold,
    }
