import yaml
from scripts.pipeline import Pipeline
from scripts.aux.reader import DataReader
from scripts.aux.transformer import DataTransformer


def load_config() -> dict:
    """Load configuration from a YAML file."""

    def load(config_path: str) -> dict:
        with open(config_path, "r", encoding="utf-8") as file:
            config = yaml.safe_load(file)
        return config

    return {
        "conab": load("config/conab.yaml"),
        "pam": load("config/pam.yaml"),
        "geom_mun": load("config/geom_mun.yaml"),
        "geom_uf": load("config/geom_uf.yaml"),
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
