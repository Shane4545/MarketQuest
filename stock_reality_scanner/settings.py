from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = PROJECT_ROOT / "config"
REPORTS_DIR = PROJECT_ROOT / "reports"
WEB_DIR = PROJECT_ROOT / "web"

# Hindsight optimizer defaults (see README): starting stake and aspirational target.
DEFAULT_STARTING_CASH = 100.0
DEFAULT_TARGET_CASH = 100_000_000.0

# From DEFAULT_STARTING_CASH to DEFAULT_TARGET_CASH requires this multiple (e.g. $100 → $100,000,000).
REQUIRED_MULTIPLE_TO_DEFAULT_TARGET = DEFAULT_TARGET_CASH / DEFAULT_STARTING_CASH
