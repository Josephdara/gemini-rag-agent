import os
from dataclasses import dataclass
from functools import cache


@dataclass(frozen=True)
class Settings:
    project: str
    chat_location: str
    chat_model: str
    embedding_model: str
    embedding_location: str
    embedding_dimensions: int
    bq_dataset: str
    bq_location: str
    top_k: int
    model_armor_template: str | None

    @property
    def chunks_table(self):
        return f"{self.project}.{self.bq_dataset}.chunks"


@cache
def settings():
    """Reads settings from the environment; Terraform's agent_env output lists the values for this project."""
    env = os.environ
    return Settings(
        project=env["GOOGLE_CLOUD_PROJECT"],
        chat_location=env.get("GOOGLE_CLOUD_LOCATION", "us"),
        chat_model=env.get("CHAT_MODEL", "gemini-3.8-flash"),
        embedding_model=env.get("EMBEDDING_MODEL", "gemini-embedding-001"),
        embedding_location=env.get("EMBEDDING_LOCATION", "us-east4"),
        embedding_dimensions=int(env.get("EMBEDDING_DIMENSIONS", "768")),
        bq_dataset=env.get("BQ_DATASET", "rag"),
        bq_location=env.get("BQ_LOCATION", "us-east4"),
        top_k=int(env.get("TOP_K", "4")),
        # Empty disables screening, which only local tests should do.
        model_armor_template=env.get("MODEL_ARMOR_TEMPLATE") or None,
    )
