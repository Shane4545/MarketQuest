from pathlib import Path


def repo_root() -> Path:
    """Resolve repository root (directory containing `app/`)."""
    here = Path(__file__).resolve()
    for p in [here.parent] + list(here.parents):
        if (p / "app").is_dir() and (p / "app" / "scripts").is_dir():
            return p
    return here.parents[3]


def app_dir() -> Path:
    return repo_root() / "app"


def data_dir() -> Path:
    return app_dir() / "data"


def raw_dir() -> Path:
    return data_dir() / "raw"


def staged_dir() -> Path:
    return data_dir() / "staged"


def features_dir() -> Path:
    return data_dir() / "features"


def curated_dir() -> Path:
    return data_dir() / "curated"


def baskets_dir() -> Path:
    return data_dir() / "baskets"


def evidence_dir() -> Path:
    return data_dir() / "evidence"


def config_dir() -> Path:
    return app_dir() / "backend" / "src" / "core" / "config"
