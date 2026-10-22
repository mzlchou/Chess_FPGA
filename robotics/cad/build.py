"""Builds every model in src/, or just the ones you name.

    python build.py                  # everything
    python build.py pieces           # one folder
    python build.py claw/jaw.py      # one file

Models import shared code from src/lib, so they need src/ on the Python path.
This script sets that up for you. Unchanged models are skipped automatically,
so running everything is cheap after the first time.
"""

import os
import pathlib
import subprocess
import sys

CAD_ROOT = pathlib.Path(__file__).resolve().parent
SRC = CAD_ROOT / "src"

# Each assembly builds any part it uses that is out of date, so the order here doesn't matter much.
FOLDER_ORDER = ["pieces", "claw", "board"]


def models_to_build(targets: list[str]) -> list[pathlib.Path]:
    if not targets:
        targets = FOLDER_ORDER
    found = []
    for target in targets:
        path = SRC / target
        if path.is_dir():
            found += sorted(p for p in path.glob("*.py") if p.name != "__init__.py")
        elif path.is_file():
            found.append(path)
        else:
            sys.exit(f"Can't find {target} in src/")
    return found


def main() -> None:
    env = dict(os.environ, PYTHONPATH=str(SRC))
    failed = []
    for model in models_to_build(sys.argv[1:]):
        name = model.relative_to(SRC).as_posix()
        print(f"building {name}", flush=True)
        result = subprocess.run([sys.executable, str(model)], cwd=CAD_ROOT, env=env, capture_output=True, text=True)
        if result.returncode != 0:
            failed.append(name)
            print(result.stdout[-2000:], result.stderr[-2000:], sep="\n")
    if failed:
        sys.exit(f"\nThese didn't build: {', '.join(failed)}")
    print("\nAll built.")


if __name__ == "__main__":
    main()
