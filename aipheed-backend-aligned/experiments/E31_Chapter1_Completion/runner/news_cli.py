"""Run the E28 news CLI under the E28 guard:  python -B runner/news_cli.py <command> [options]"""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BD = HERE.parent / "backend_dev"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(BD))
import guard31  # noqa: E402

guard31.install()
os.chdir(BD)
from scripts.news_collect import main  # noqa: E402

raise SystemExit(main(sys.argv[1:]))
