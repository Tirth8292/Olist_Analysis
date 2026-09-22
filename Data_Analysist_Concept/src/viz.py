from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from src.data_utils import FIGURES_DIR

sns.set_theme(style="whitegrid")


def _save(fig, save_path: str | None) -> None:
    if save_path:
        FIGURES_DIR.mkdir(parents=True, exist_ok=True)
        fig.savefig(FIGURES_DIR / save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_count(df: pd.DataFrame, column: str, title: str = "", xlabel: str = "", ylabel: str = "Count", save_path: str | None = None):
    fig, ax = plt.subplots(figsize=(8, 5))
    sns.countplot(data=df, x=column, ax=ax, palette="viridis", legend=False)
    ax.set_title(title)
    ax.set_xlabel(xlabel or column)
    ax.set_ylabel(ylabel)
    _save(fig, save_path)
    return fig


def plot_bar(x, y, title: str = "", xlabel: str = "", ylabel: str = "", orientation: str = "v", save_path: str | None = None):
    fig, ax = plt.subplots(figsize=(10, 6))
    if orientation == "h":
        ax.barh(list(map(str, y)), x, color=sns.color_palette("viridis", len(list(y))))
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.invert_yaxis()
    else:
        ax.bar(list(map(str, x)), y, color=sns.color_palette("viridis", len(list(x))))
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
    ax.set_title(title)
    _save(fig, save_path)
    return fig


def plot_line(data, title: str = "", xlabel: str = "", ylabel: str = "", save_path: str | None = None):
    fig, ax = plt.subplots(figsize=(12, 6))
    x = data.index.astype(str)
    ax.plot(x, data.values, marker="o")
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
    _save(fig, save_path)
    return fig


def line_plot(x, y, title: str = "", xlabel: str = "", ylabel: str = "", save_path: str | None = None):
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(x, y, marker="o")
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    _save(fig, save_path)
    return fig


def plot_box(df: pd.DataFrame, x: str, y: str, title: str = "", xlabel: str = "", ylabel: str = "", hue: str | None = None, save_path: str | None = None):
    fig, ax = plt.subplots(figsize=(10, 6))
    if hue:
        sns.boxplot(data=df, x=x, y=y, hue=hue, ax=ax, palette="Set2")
    else:
        sns.boxplot(data=df, x=x, y=y, ax=ax, palette="Set2")
    ax.set_title(title)
    ax.set_xlabel(xlabel or x)
    ax.set_ylabel(ylabel or y)
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
    _save(fig, save_path)
    return fig


def plot_stacked_bar(data: pd.DataFrame, title: str = "", xlabel: str = "", ylabel: str = "", save_path: str | None = None):
    fig, ax = plt.subplots(figsize=(10, 6))
    data.plot(kind="bar", stacked=True, ax=ax, colormap="viridis")
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    _save(fig, save_path)
    return fig


def plot_heatmap(data, title: str = "", xlabel: str = "", ylabel: str = "", save_path: str | None = None):
    fig, ax = plt.subplots(figsize=(9, 7))
    sns.heatmap(data, annot=True, fmt=".2f", cmap="coolwarm", ax=ax)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    _save(fig, save_path)
    return fig


def plot_scatter(x, y, title: str = "", xlabel: str = "", ylabel: str = "", save_path: str | None = None):
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.scatter(x, y, alpha=0.4, s=15, color="steelblue")
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    _save(fig, save_path)
    return fig


def plot_bubble(data: pd.DataFrame, x_col: str, y_col: str, size_col: str, title: str = "", xlabel: str = "", ylabel: str = "", top_n_labels: int = 10, save_path: str | None = None):
    fig, ax = plt.subplots(figsize=(12, 8))
    sizes = data[size_col] / data[size_col].max() * 2000 + 30
    ax.scatter(data[x_col], data[y_col], s=sizes, alpha=0.5, color="teal", edgecolors="black")
    label_data = data.sort_values(size_col, ascending=False).head(top_n_labels)
    for name, row in label_data.iterrows():
        ax.annotate(str(name), (row[x_col], row[y_col]), fontsize=8, xytext=(4, 4), textcoords="offset points")
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    _save(fig, save_path)
    return fig


def pie_plot(data: pd.Series, title: str = "", save_path: str | None = None):
    fig, ax = plt.subplots(figsize=(8, 8))
    ax.pie(data.values, labels=data.index, autopct="%1.1f%%", colors=sns.color_palette("viridis", len(data)))
    ax.set_title(title)
    _save(fig, save_path)
    return fig
