"""Install the E12 guard first; tests use synthetic data only."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "runner"))
import guard  # noqa: E402
guard.install()
