from typing import Dict, Any, Protocol
import pandas as pd
from tqdm import tqdm


class DataReader(Protocol):
    def read(self) -> Dict[str, Any]: ...


class DataTransformer(Protocol):
    def transform(self, data: Dict[str, Any]) -> Dict[str, Any]: ...


class DataVizualizer(Protocol):
    def vizualize(self, data: Dict[str, pd.DataFrame]) -> None: ...
class Pipeline:
    def __init__(
        self,
        reader: DataReader,
        transformer: DataTransformer,
        vizualizer: DataVizualizer,
    ) -> None:
        self.reader = reader
        self.transformer = transformer
        self.vizualizer = vizualizer

    def save_data(self, data: dict[str, pd.DataFrame]) -> None:
        """Save transformed data to disk."""
        for key, table in tqdm(data.items(), desc="Saving data"):
            table.to_parquet(f"data/{key}.parquet", index=False)

    def run(self) -> None:
        """Execute the data pipeline."""
        data = self.reader.read()
        transformed_data = self.transformer.transform(data)
        self.vizualizer.vizualize(transformed_data)
        self.save_data(transformed_data)
