import os
import pandas as pd
import matplotlib.pyplot as plt
from typing import Dict, Any, Protocol, Type, List


# --- Protocols ---


class PlotStrategy(Protocol):
    """Interface for complex multi-DataFrame plotting strategies."""

    def apply(self, data: Dict[str, pd.DataFrame], params: Any) -> None: ...


class PlotDivergenceLineStrategy:
    """
    Generates plots to visualize divergences between datasets.
    It wants to respond to this specific question: "How do the values of CONAB and PAM columns diverge over time across different states?"
    """

    def apply(self, data: Dict[str, pd.DataFrame], params: Dict[str, Any]) -> None:

        table_name = params.get("dataframe", "")
        group_cols = params.get("group_cols", "")
        x_cols = params.get("x_cols", "")
        y_cols = params.get("y_cols", [])
        analysis_cols = params.get("analysis_cols", "")
        titles = params.get("titles", "Divergence Line Plot")
        subtitles = params.get("subtitles", "")
        x_labels = params.get("x_labels", x_cols)
        y_labels = params.get("y_labels", y_cols)
        rate_suffixes = params.get("rate_suffixes", [])
        recalculate_rates = params.get("recalculate_rates", [])
        add_straight_line = params.get("add_straight_line", [])
        output_files = params.get("output_files", "./plots/")

        df = data[table_name].copy()

        for i, cols in enumerate(analysis_cols):
            df = df.groupby(group_cols[i]).sum(numeric_only=True).reset_index()
            if recalculate_rates[i]:
                col_base = "_".join(y_cols[i].split("_")[1:-2])
                r1 = rate_suffixes[0]
                r2 = rate_suffixes[1]
                df[y_cols[i]] = df[f"{col_base}_{r1}"] / df[f"{col_base}_{r2}"]

            _, ax = plt.subplots(figsize=(12, 8))

            # Set white background and remove spines (bounding box)
            ax.set_facecolor("white")
            for spine in ax.spines.values():
                spine.set_visible(False)

            for label, grp in df.groupby(cols):
                (line,) = ax.plot(
                    grp[x_cols[i]], grp[y_cols[i]], label=label, marker="o"
                )

                # Add label at the end of the line
                y_pos = grp[y_cols[i]].iloc[-1]
                x_pos = grp[x_cols[i]].iloc[-1]
                ax.text(
                    x_pos,
                    y_pos,
                    f" {label}",
                    verticalalignment="center",
                    color=line.get_color(),
                    fontsize=10,
                )

            if add_straight_line[i][0]:
                ax.axhline(
                    y=add_straight_line[i][1],
                    color="black",
                    linestyle="--",
                    linewidth=1,
                )
            plt.suptitle(titles[i], fontsize=16, fontweight="bold")
            plt.title(subtitles[i], fontsize=12)
            plt.ylabel(y_labels[i], fontsize=12)
            plt.xlabel(x_labels[i], fontsize=12)

            # Remove legend since labels are on the lines
            # plt.legend(title=analysis_cols[i], bbox_to_anchor=(1.05, 1), loc="upper left")

            plt.grid(True, linestyle="--", alpha=0.7)
            plt.tight_layout()
            os.makedirs(os.path.dirname(output_files[i]), exist_ok=True)
            plt.savefig(output_files[i], dpi=300, bbox_inches="tight")
            plt.close()


class PlotDivergenceScatterStrategy:
    """
    Generates scatter plots to visualize divergences between datasets.
    """

    def apply(self, data: Dict[str, pd.DataFrame], params: Dict[str, Any]) -> None:

        table_name = params.get("dataframe", "")
        x_cols = params.get("x_cols", "")
        y_cols = params.get("y_cols", "")
        color_cols = params.get("color_cols", "")
        analysis_cols = params.get("analysis_cols", "")
        titles = params.get("titles", "Divergence Scatter Plot")
        subtitles = params.get("subtitles", "")
        add_straight_line = params.get("add_straight_line", False)
        x_labels = params.get("x_labels", x_cols)
        y_labels = params.get("y_labels", y_cols)
        output_files = params.get("output_files", ["./plots/scatter_plot.png"])

        df = data[table_name].copy()

        for i, analysis_col in enumerate(analysis_cols):
            _, ax = plt.subplots(figsize=(12, 8))

            ax.set_facecolor("white")
            for spine in ax.spines.values():
                spine.set_visible(False)

            for label, grp in df.groupby(analysis_col):
                import ipdb

                ipdb.set_trace()

                if color_cols[i] == "":
                    grp.plot.scatter(x=x_cols[i], y=y_cols[i], ax=ax, label=label)
                else:
                    color_values = df[color_cols[i]].unique()

                    color_map = dict(
                        zip(
                            color_values,
                            plt.cm.tab10.colors[: len(color_values)],
                        )
                    )
                    grp.plot.scatter(
                        x=x_cols[i],
                        y=y_cols[i],
                        ax=ax,
                        label=label,
                        c=grp[color_cols[i]].map(color_map),
                    )

                # Add labels to each scatter point
                for _, row in grp.iterrows():
                    ax.text(
                        row[x_cols[i]],
                        row[y_cols[i]],
                        f" {row[analysis_col].values[-1]}",
                        fontsize=9,
                        verticalalignment="bottom",
                    )

            if add_straight_line:
                max_val = max(df[x_cols[i]].max(), df[y_cols[i]].max())
                ax.plot(
                    [0, max_val], [0, max_val], color="red", linestyle="--", linewidth=1
                )
            plt.suptitle(titles[i], fontsize=16, fontweight="bold")
            plt.title(subtitles[i], fontsize=12)
            plt.ylabel(y_labels[i], fontsize=12)
            plt.xlabel(x_labels[i], fontsize=12)
            # plt.legend(title=analysis_col, bbox_to_anchor=(1.05, 1), loc="upper left")
            plt.grid(True, linestyle="--", alpha=0.7)
            plt.tight_layout()
            os.makedirs(os.path.dirname(output_files[i]), exist_ok=True)
            plt.savefig(output_files[i], dpi=300, bbox_inches="tight")
            plt.close()


class DataVizualizer:
    """
    Handles visualization strategies for multiple DataFrames.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._plot_strategies: Dict[str, Type[PlotStrategy]] = {
            "plot_divergence_line": PlotDivergenceLineStrategy,
            "plot_divergence_scatter": PlotDivergenceScatterStrategy,
        }

    def handle_plots(self, data: Dict[str, pd.DataFrame]) -> None:
        """
        Handle plotting based on configuration.
        Iterates through registered plot strategies and applies them if present in config.
        """
        for key in list(data.keys()):
            dataset_config = self.config.get(key, {})
            vizualize_config = dataset_config.get("vizualize", {})

            for plot_name, strategy_cls in self._plot_strategies.items():
                plot_params = vizualize_config.get(plot_name)
                if plot_params:
                    strategy = strategy_cls()
                    strategy.apply(data, plot_params)

    def vizualize(self, data: Dict[str, pd.DataFrame]) -> None:
        """
        Main method to handle all visualizations.
        """
        print("--------- Starting data visualization ---------")
        self.handle_plots(data)
