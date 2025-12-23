import pandas as pd
from typing import Dict, Any, Protocol, Type


class TransformationStrategy(Protocol):
    """Interface for transformation strategies."""

    def apply(self, df: pd.DataFrame, params: Any) -> pd.DataFrame: ...


class RenameColumnsStrategy:
    """Rename columns in a DataFrame based on provided parameters."""

    def apply(self, df: pd.DataFrame, params: Dict[str, str]) -> pd.DataFrame:
        return df.rename(columns=params)[list(params.values())]


class PivotTableStrategy:
    """Pivot a DataFrame based on provided parameters."""

    def apply(self, df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
        return df.pivot_table(
            index=params["index"],
            columns=params["columns"],
            values=params["values"],
        ).reset_index()


class FilterRowsStrategy:
    """Filter rows in a DataFrame based on provided parameters."""

    def apply(self, df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
        for col, val in params.items():
            if isinstance(val, list):
                df = df[df[col].isin(val)]
            else:
                df = df[df[col] == val]
        return df


class DtypeConversionStrategy:
    """Convert data types of DataFrame columns based on provided parameters."""

    def apply(self, df: pd.DataFrame, params: Dict[str, str]) -> pd.DataFrame:

        for col, dtype in params.items():
            if dtype == "float":
                df[col] = pd.to_numeric(df[col], errors="coerce")
            else:
                df[col] = df[col].astype(dtype)
        return df


class ChangeUnitsStrategy:
    """Change units of DataFrame columns based on provided parameters."""

    def apply(self, df: pd.DataFrame, params: Dict[str, float]) -> pd.DataFrame:
        for col, factor in params.items():
            if col in df.columns:
                df[col] = df[col] * factor
        return df


class TransformColumnsStrategy:
    """Apply transformations to DataFrame columns based on provided parameters."""

    def apply(self, df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
        for col, func_str in params.items():
            if col in df.columns:
                if isinstance(func_str, str) and func_str.strip().startswith("lambda"):
                    func = eval(func_str)
                    df[col] = df[col].apply(func)
                elif callable(func_str):
                    df[col] = df[col].apply(func_str)
        return df


class DataTransformer:
    """
    A class to transform pandas DataFrames based on a given configuration.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._strategies: Dict[str, Type[TransformationStrategy]] = {
            "rename_columns": RenameColumnsStrategy,
            "pivot_table": PivotTableStrategy,
            "filter_rows": FilterRowsStrategy,
            "dtype_conversion": DtypeConversionStrategy,
            "change_units": ChangeUnitsStrategy,
            "transform_columns": TransformColumnsStrategy,
        }

    def _merge_table(
        self, data: Dict[str, pd.DataFrame], main_key: str, params: Dict[str, Any]
    ) -> pd.DataFrame:
        df = data[main_key]
        for table_name, merge_params in params.items():
            if table_name not in data:
                continue
            other_df = data[table_name]
            on = merge_params.get("merge_on")
            how = merge_params.get("how", "inner")
            suffixes = merge_params.get("suffixes", ("_x", "_y"))
            df = df.merge(other_df, on=on, how=how, suffixes=suffixes)
        return df

    def handle_transformations(
        self, data: Dict[str, pd.DataFrame]
    ) -> Dict[str, pd.DataFrame]:
        """Handle simple transformations on the data."""
        for key in list(data.keys()):
            dataset_config = self.config.get(key, {})
            transformations = dataset_config.get("transform", {}).get(
                "simple_transformations", {}
            )

            for trans_name, params in transformations.items():
                strategy_cls = self._strategies.get(trans_name)
                if strategy_cls:
                    strategy = strategy_cls()
                    data[key] = strategy.apply(data[key], params)
        return data

    def handle_joins(self, data: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
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
                group_cols = groupby_params.get("group_cols", [])
                agg_params = groupby_params.get("aggregations", {})
                table_to_group = groupby_params.get("dataframe", "")
                data[output_name] = (
                    data[table_to_group]
                    .groupby(group_cols, as_index=False)
                    .agg(agg_params)
                )
        return data

    def transform(self, data: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """Transform the data based on configuration."""
        data = self.handle_transformations(data)
        data = self.handle_joins(data)
        data = self.handle_groupbys(data)
        import ipdb

        ipdb.set_trace()
        return data
