"""Install the E11 guard before any test module is imported. Tests use synthetic data only."""
import sys
from pathlib import Path

RUNNER = Path(__file__).resolve().parents[1] / "runner"
sys.path.insert(0, str(RUNNER))
import guard  # noqa: E402

guard.install()
