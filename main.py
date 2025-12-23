import yaml
from src.pipeline import Pipeline
from src.reader import DataReader
from src.transformer import DataTransformer


def load_config() -> dict:
    """Load configuration from a YAML file."""

    def load(config_path: str) -> dict:
        with open(config_path, "r", encoding="utf-8") as file:
            config = yaml.safe_load(file)
        return config

    return {
        "conab": load("config/conab.yaml"),
        "pam": load("config/pam.yaml"),
        "mun": load("config/mun_uf.yaml"),
    }


def main():
    """Main function to demonstrate data reading."""
    config = load_config()
    reader = DataReader(config)
    transformer = DataTransformer(config)
    pipeline = Pipeline(reader, transformer)
    pipeline.run()


if __name__ == "__main__":
    main()
