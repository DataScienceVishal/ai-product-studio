"""Freeze the prompt, schema and run configuration: write FROZEN.json with their SHA-256 (KILL-TEST.md section 1).

Run once, after prompt and reasoning-effort work on the DEV set is finished, and commit FROZEN.json before the held-out layouts
are written and before any TEST run. extract.py refuses `--set test` if extract_config.py no longer matches this hash.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

import extract_config as cfg

OUT = Path(__file__).resolve().parent / "FROZEN.json"

if __name__ == "__main__":
    if OUT.exists():
        raise SystemExit(f"{OUT} already exists; a freeze is final. Amendments are dated and kept in the idea file.")
    OUT.write_text(json.dumps({"sha256": cfg.frozen_hash(), "frozen_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                               "reasoning_effort": cfg.CONFIG["reasoning_effort"], "price_model": cfg.CONFIG["price_model"]}, indent=1) + "\n")
    print(f"froze extract_config.py: sha256 {cfg.frozen_hash()}")
