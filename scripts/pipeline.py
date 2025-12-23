from typing import Dict, Any, Protocol
import pandas as pd


class DataReader(Protocol):
    def read(self) -> Dict[str, Any]: ...


class DataTransformer(Protocol):
    def transform(self, data: Dict[str, Any]) -> Dict[str, Any]: ...


class Pipeline:
    def __init__(self, reader: DataReader, transformer: DataTransformer):
        self.reader = reader
        self.transformer = transformer

    def save_data(self, data: dict[str, pd.DataFrame]) -> None:
        """Save transformed data to disk."""
        for key, table in data.items():
            table.to_csv(f"data/{key}.csv", index=False)

    def run(self) -> None:
        """Execute the data pipeline."""
        data = self.reader.read()
        transformed_data = self.transformer.transform(data)
        self.save_data(transformed_data)
