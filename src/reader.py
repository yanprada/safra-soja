"""
Reader module to handle data reading from Conab and PAM sources.
"""

from dataclasses import dataclass
import pandas as pd
from tqdm import tqdm
import sidrapy


@dataclass
class Data:
    """
    Parameters for reading data.
    """

    read: dict
    transform: dict[str, dict[str, str]]


class DataReader:
    """
    Reader class to handle data reading from Conab and PAM sources.
    """

    def __init__(self, config: dict):
        self.config = config
        self.conab_params = Data(**self.config["conab"])
        self.pam_params = Data(**self.config["pam"])
        self.mun_params = Data(**self.config["mun"])

    def read_conab(self) -> pd.DataFrame:
        """Read Conab data from a CSV file."""
        params = self.conab_params.read
        return pd.read_csv(
            params.get("url"),
            sep=params.get("sep"),
            encoding=params.get("encoding"),
        )

    def read_pam(self) -> pd.DataFrame:
        """Read PAM data using sidrapy."""
        params = self.pam_params.read
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
        return pd.concat(dfs, ignore_index=True)

    def read_mun(self) -> pd.DataFrame:
        """Read municipal data from a CSV file."""
        params = self.mun_params.read
        return pd.read_csv(
            params.get("url"),
            sep=params.get("sep"),
            encoding=params.get("encoding"),
        )

    def read(self) -> dict[str, pd.DataFrame]:
        """Read data from both Conab and PAM sources."""
        conab_data = self.read_conab()
        pam_data = self.read_pam()
        mun_data = self.read_mun()
        return {"conab": conab_data, "pam": pam_data, "mun": mun_data}
