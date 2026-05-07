import os
import sys
from pathlib import Path

# Settings instantiates eagerly on import; populate the env before any
# banger_link.* import runs.
os.environ.setdefault("TELEGRAM_TOKEN", "stub:token-for-tests")
os.environ.setdefault("DATA_DIR", "/tmp/banger_link_test_data")
os.environ.setdefault("LOG_LEVEL", "WARNING")

Path(os.environ["DATA_DIR"]).mkdir(parents=True, exist_ok=True)

# Ensure the project root is on the path when pytest is invoked from elsewhere.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
