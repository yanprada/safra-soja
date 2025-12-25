"""
Reader module to handle data reading from Conab and PAM sources.
"""

from dataclasses import dataclass
import geopandas as gpd
import pandas as pd
from tqdm import tqdm
import sidrapy
import os


@dataclass
class Data:
    """
    Parameters for reading data.
    """

    read: dict
    transform: dict[str, dict[str, str]]
    vizualize: dict[str, dict[str, str]]


class DataReader:
    """
    Reader class to handle data reading from Conab and PAM sources.
    """

    def __init__(self, config: dict):
        self.config = config
        self.conab_params = Data(**self.config["conab"])
        self.pam_params = Data(**self.config["pam"])
        self.mun_params = Data(**self.config["geom_mun"])
        self.uf_params = Data(**self.config["geom_uf"])

    def read_conab(self) -> pd.DataFrame:
        """Read Conab data from a CSV file."""
        params = self.conab_params.read
        return pd.read_csv(
            params.get("url"),
            sep=params.get("sep"),
            encoding=params.get("encoding"),
        )

    def read_pam(self) -> pd.DataFrame:
        """Read PAM data using sidrapy with caching."""
        params = self.pam_params.read
        cache_file = params.get("cache_file")
        if os.path.exists(cache_file):
            return pd.read_parquet(cache_file)

        dfs = []
        for year in tqdm(params.get("period", []), desc="Reading PAM data"):
            df = sidrapy.get_table(
                table_code=params.get("table_code"),
                territorial_level=params.get("territorial_level"),
                ibge_territorial_code=params.get("ibge_territorial_code"),
                period=year,
                classifications=params.get("filter_class"),
            )
            dfs.append(df)

        final_df = pd.concat(dfs, ignore_index=True)
        os.makedirs(os.path.dirname(cache_file), exist_ok=True)
        final_df.to_parquet(cache_file, index=False)
        return final_df

    def read_geom_mun(self) -> pd.DataFrame:
        """Read geometries for Brazilian municipalities."""
        params = self.mun_params.read
        url = params.get("url")
        return gpd.read_file(url)

    def read_geom_uf(self) -> gpd.GeoDataFrame:
        """Read geometries for Brazilian states."""
        params = self.uf_params.read
        url = params.get("url")
        return gpd.read_file(url)

    def read(self) -> dict[str, pd.DataFrame]:
        """Read data from both Conab and PAM sources."""
        print("--------- Starting data reading ---------")
        conab_data = self.read_conab()
        geom_mun_data = self.read_geom_mun()
        geom_uf_data = self.read_geom_uf()
        pam_data = self.read_pam()
        return {
            "conab": conab_data,
            "pam": pam_data,
            "geom_mun": geom_mun_data,
            "geom_uf": geom_uf_data,
        }
