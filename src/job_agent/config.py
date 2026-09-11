"""Loads config/companies.yaml — the list of boards/clients/tags to pull from."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "companies.yaml"


@dataclass
class SourcesConfig:
    greenhouse_boards: list[str]
    lever_clients: list[str]
    remoteok_tags: list[str]


def load_sources_config(path: Path | str = DEFAULT_CONFIG_PATH) -> SourcesConfig:
    with open(path) as f:
        data = yaml.safe_load(f) or {}

    return SourcesConfig(
        greenhouse_boards=data.get("greenhouse_boards", []) or [],
        lever_clients=data.get("lever_clients", []) or [],
        remoteok_tags=data.get("remoteok_tags", []) or [],
    )
