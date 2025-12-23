import pandas as pd
from functools import reduce
from typing import Dict, Any, Protocol, Type, List


# --- Protocols ---


class TransformationStrategy(Protocol):
    """Interface for simple single-DataFrame transformation strategies."""

    def apply(self, df: pd.DataFrame, params: Any) -> pd.DataFrame: ...


class CalculationStrategy(Protocol):
    """Interface for complex multi-DataFrame calculation strategies."""

    def apply(
        self, data: Dict[str, pd.DataFrame], params: Any
    ) -> Dict[str, pd.DataFrame]: ...


# --- Simple Transformation Strategies ---


class RenameColumnsStrategy:
    def apply(self, df: pd.DataFrame, params: Dict[str, str]) -> pd.DataFrame:
        return df.rename(columns=params)[list(params.values())]


class PivotTableStrategy:
    def apply(self, df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
        return df.pivot_table(
            index=params["index"],
            columns=params["columns"],
            values=params["values"],
        ).reset_index()


class FilterRowsStrategy:
    def apply(self, df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
        for col, val in params.items():
            if isinstance(val, list):
                df = df[df[col].isin(val)]
            else:
                df = df[df[col] == val]
        return df


class DtypeConversionStrategy:
    def apply(self, df: pd.DataFrame, params: Dict[str, str]) -> pd.DataFrame:
        for col, dtype in params.items():
            if col not in df.columns:
                continue
            if dtype == "float":
                df[col] = pd.to_numeric(df[col], errors="coerce")
            else:
                df[col] = df[col].astype(dtype)
        return df


class ChangeUnitsStrategy:
    def apply(self, df: pd.DataFrame, params: Dict[str, float]) -> pd.DataFrame:
        for col, factor in params.items():
            if col in df.columns:
                df[col] = df[col] * factor
        return df


class TransformColumnsStrategy:
    def apply(self, df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
        for col, func_str in params.items():
            if col in df.columns:
                # Note: eval is risky. In production, prefer a registry of allowed functions.
                if isinstance(func_str, str) and func_str.strip().startswith("lambda"):
                    func = eval(func_str)
                    df[col] = df[col].apply(func)
                elif callable(func_str):
                    df[col] = df[col].apply(func_str)
        return df


# --- Calculation Strategies ---


class CalculateDiffStrategy:
    """Calculates difference between PAM and CONAB data."""

    def apply(
        self, data: Dict[str, pd.DataFrame], params: Dict[str, Any]
    ) -> Dict[str, pd.DataFrame]:
        table = params.get("dataframe", "")
        output_name = params.get("output_name", table)
        value_cols = params.get("value_cols", {})
        group_cols = params.get("group_cols", [])
        dfs = []
        for col_pam, col_conab in value_cols.items():
            diff_col = f"diff_{col_pam.replace('_pam', '')}_conab_pam"
            pct_col = f"rate_{col_pam.replace('_pam', '')}_conab_pam"
            df = data[table].copy()
            df[diff_col] = df[col_conab] - df[col_pam]
            df[pct_col] = (df[diff_col] / df[col_pam].replace(0, pd.NA)).fillna(0)
            dfs.append(df[group_cols + [diff_col, pct_col]])
        dfs.append(data[table])
        if dfs:
            data[output_name] = reduce(
                lambda left, right: pd.merge(left, right, on=group_cols), dfs
            )
        return data


class CalculatePctStrategy:
    """Calculates percentage of municipality vs UF total."""

    def test_pct_mun_uf(
        self, df: pd.DataFrame, join_cols: List[str], used_cols: List[str]
    ) -> Dict[str, pd.DataFrame]:
        """Tests if the percentage columns sum to 1 for each year and state."""
        for year, state in df[join_cols].drop_duplicates().values:
            for col in used_cols:
                pct_col = f"pct_mun_uf_{col}"
                if pct_col not in df.columns:
                    continue
                sample = df[(df[join_cols[0]] == year) & (df[join_cols[1]] == state)][
                    [col, pct_col]
                ]
                total = sample[col].sum()
                pct_sum = sample[pct_col].sum()
                if not pd.isna(total) and total != 0:
                    assert abs(pct_sum - 1.0) < 1e-6, (
                        f"Percentage sum for {col} in {state} ({year}) "
                        f"does not equal 1. Found: {pct_sum}"
                    )
        return df

    def apply(
        self, data: Dict[str, pd.DataFrame], params: Dict[str, Any]
    ) -> Dict[str, pd.DataFrame]:
        table1, table2 = params.get("dataframes", ["", ""])
        if table1 not in data or table2 not in data:
            return data

        join_cols = params.get("join_cols", [])
        used_cols = params.get("used_cols", [])
        output_name = params.get("output_name", f"{table1}_pct")

        df_mun = data[table1].copy()
        df_uf = data[table2].copy()

        merged_df = df_mun.merge(
            df_uf, on=join_cols, how="left", suffixes=("", "_uf_total")
        )

        for col in used_cols:
            pct_col = f"pct_mun_uf_{col}"
            col_uf = f"{col}_uf_total"
            if col_uf not in merged_df.columns:
                continue
            merged_df[pct_col] = merged_df[col] / merged_df[col_uf]
        self.test_pct_mun_uf(merged_df, join_cols, used_cols)
        data[output_name] = merged_df
        return data


class CalculateProjectionStrategy:
    """Projects PAM data for the next year."""

    def apply(
        self, data: Dict[str, pd.DataFrame], params: Dict[str, Any]
    ) -> Dict[str, pd.DataFrame]:
        table_name_pct, table_name_total = params.get("dataframes", "")
        year = params.get("reference_year", "")
        proj_year = params.get("projected_year", "")
        value_cols = params.get("value_cols", {})
        group_cols = params.get("group_cols", [])
        level_analysis = params.get("level_analysis", "")

        df_pct = data[table_name_pct].copy()
        df_next_year = data[table_name_total].copy()

        df_pct_year = df_pct[df_pct["ano"] == year][
            list(value_cols.keys()) + group_cols + [level_analysis]
        ]
        df_next_year_year = df_next_year[df_next_year["ano"] == proj_year][
            list(value_cols.values()) + group_cols
        ]
        df = df_next_year_year.merge(
            df_pct_year, on=group_cols, how="inner", suffixes=("", "_pct")
        )
        df["ano"] = proj_year
        for col_pct_mun, col_uf in value_cols.items():
            projected_col = f"projected_{col_uf}"
            df[projected_col] = df[col_uf] * df[col_pct_mun]
        output_name = params.get("output_name", "pam_projected")
        data[output_name] = df
        return data


class CalculateCorrStrategy:
    """Calculates correlation between area and productivity."""

    def apply(
        self, data: Dict[str, pd.DataFrame], params: Dict[str, Any]
    ) -> Dict[str, pd.DataFrame]:
        table_name = params.get("dataframe", "")
        area_col = params.get("area_col", "area_plantada_ha_pam")
        prod_col = params.get("productivity_col", "rendimento_medio_kg_ha_pam")
        output_name = params.get("output_name", "area_productivity_correlation")

        df = data[table_name].copy()
        corr = df[area_col].corr(df[prod_col])
        data[output_name] = pd.DataFrame(
            {
                "correlation": [corr],
                "area_col": [area_col],
                "productivity_col": [prod_col],
                "table": [table_name],
            }
        )
        return data


class CalculateAreaGrowthStrategy:
    """Calculates production and area growth over years."""

    def apply(
        self, data: Dict[str, pd.DataFrame], params: Dict[str, Any]
    ) -> Dict[str, pd.DataFrame]:
        """Calculates production and area growth over years."""
        table_names = params.get("dataframes", [])
        group_cols = params.get("group_cols", [])
        base_year = params.get("base_year", "")
        target_year = params.get("target_year", "")
        value_cols = params.get("value_cols", [])
        output_name = params.get("output_name", "production_area_growth")
        for i, table_name in enumerate(table_names):
            df = data[table_name].copy()
            import ipdb

            ipdb.set_trace()
            df_base = df[df["ano"] == base_year][value_cols + group_cols[i]]
            df_target = df[df["ano"] == target_year][value_cols + group_cols[i]]
            df_merged = df_base.merge(
                df_target, on=group_cols[i], suffixes=("_base", "_target")
            )
            for col in value_cols:
                growth_col = f"growth_{col}"
                df_merged[growth_col] = (
                    (df_merged[f"{col}_target"] - df_merged[f"{col}_base"])
                    / df_merged[f"{col}_base"].replace(0, pd.NA)
                ).fillna(0)

            data[output_name + "_" + table_name] = df_merged
        return data


# --- Main Transformer ---


class DataTransformer:
    """
    A class to transform pandas DataFrames based on a given strategy configuration.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config

        # Registry for simple transformations (DF -> DF)
        self._simple_strategies: Dict[str, Type[TransformationStrategy]] = {
            "rename_columns": RenameColumnsStrategy,
            "pivot_table": PivotTableStrategy,
            "filter_rows": FilterRowsStrategy,
            "dtype_conversion": DtypeConversionStrategy,
            "change_units": ChangeUnitsStrategy,
            "transform_columns": TransformColumnsStrategy,
        }

        # Registry for complex calculations (Dict[DF] -> Dict[DF])
        self._calculation_strategies: Dict[str, Type[CalculationStrategy]] = {
            "calculate_diff_pam_conab": CalculateDiffStrategy,
            "calculate_pct_mun_uf": CalculatePctStrategy,
            "project_pam_next_year": CalculateProjectionStrategy,
            "calculate_area_productivity_correlation": CalculateCorrStrategy,
            "calculate_production_area_growth": CalculateAreaGrowthStrategy,
        }

    def _merge_table(
        self, data: Dict[str, pd.DataFrame], main_key: str, params: Dict[str, Any]
    ) -> pd.DataFrame:
        df = data[main_key]
        for table_name, merge_params in params.items():
            if table_name not in data:
                continue
            other_df = data[table_name]
            df = df.merge(
                other_df,
                on=merge_params.get("merge_on"),
                how=merge_params.get("how", "inner"),
                suffixes=merge_params.get("suffixes", ("_x", "_y")),
            )
        return df

    def handle_simple_transformations(
        self, data: Dict[str, pd.DataFrame]
    ) -> Dict[str, pd.DataFrame]:
        """Handle simple transformations on the data."""
        for key, _ in data.items():
            dataset_config = self.config.get(key, {})
            transformations = dataset_config.get("transform", {}).get(
                "simple_transformations", {}
            )

            for transf_name, params in transformations.items():
                strategy_cls = self._simple_strategies.get(transf_name)
                if strategy_cls:
                    data[key] = strategy_cls().apply(data[key], params)
        return data

    def handle_merges(self, data: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """Handle joining of dataframes based on configuration."""
        for key in list(data.keys()):
            dataset_config = self.config.get(key, {})
            merge_params = dataset_config.get("transform", {}).get("merge", {})
            if merge_params:
                print(f"Joining data starting with base table: {key}")
                output_name = merge_params.get("output_name", "results")
                data[output_name] = self._merge_table(
                    data, key, merge_params.get("tables", {})
                )
        return data

    def handle_groupbys(self, data: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """Handle groupby operations based on configuration."""
        for key in list(data.keys()):
            dataset_config = self.config.get(key, {})
            groupby_params = dataset_config.get("transform", {}).get("groupby", {})
            if groupby_params:
                output_name = groupby_params.get("output_name", "results")
                table_to_group = groupby_params.get("dataframe", "")

                if table_to_group in data:
                    data[output_name] = (
                        data[table_to_group]
                        .groupby(groupby_params.get("group_cols", []), as_index=False)
                        .agg(groupby_params.get("aggregations", {}))
                    )
        return data

    def handle_calculations(
        self, data: Dict[str, pd.DataFrame]
    ) -> Dict[str, pd.DataFrame]:
        """
        Handle calculations based on configuration.
        Iterates through registered calculation strategies and applies them if present in config.
        """
        for key in list(data.keys()):
            dataset_config = self.config.get(key, {})
            transform_config = dataset_config.get("transform", {})

            for calc_name, strategy_cls in self._calculation_strategies.items():
                calc_params = transform_config.get(calc_name)
                if calc_params:
                    strategy = strategy_cls()
                    data = strategy.apply(data, calc_params)

        return data

    def transform(self, data: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """Transform the data based on configuration."""
        data = self.handle_simple_transformations(data)
        data = self.handle_merges(data)
        data = self.handle_groupbys(data)
        data = self.handle_calculations(data)
        import ipdb

        ipdb.set_trace()
        return data
