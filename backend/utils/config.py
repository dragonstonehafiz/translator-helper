from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
FILES_DIR = BACKEND_DIR / "files"
CONFIG_DIR = FILES_DIR / "config"
LIBRARY_DIR = FILES_DIR / "library"
OUTPUTS_DIR = FILES_DIR / "outputs"
LOGS_DIR = FILES_DIR / "logs"
