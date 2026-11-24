"""The only benchmark module the extractor imports: the closed vocabularies and the PLAUSIBLE map (benchmark/taxonomy.py).
Domain knowledge given to the model; contains no sheet data or answers."""
import sys
from pathlib import Path

_BENCH = Path(__file__).resolve().parents[1] / "benchmark"
if str(_BENCH) not in sys.path:
    sys.path.insert(0, str(_BENCH))
import taxonomy as tx  # noqa: E402,F401

PLAUSIBLE = tx.PLAUSIBLE
MATERIALS = list(tx.MATERIAL_VOCAB)
COLOURS = list(tx.COLOUR_VOCAB)
FEATURE_VOCAB = {k: list(v) for k, v in tx.VOCAB.items()}
COMPONENT_NAMES = list(tx.NAME_VARIANTS)

# RAM category derived from the canonical material (domain mapping, applied in code, not asked of the model).
RAM_CATEGORY = {
    "PET": "plastic", "rPET": "plastic", "PETG": "plastic", "HDPE": "plastic", "PP": "plastic", "PS": "plastic",
    "PVC": "plastic", "PE/PET laminate": "plastic", "glass": "glass", "aluminium": "aluminium", "steel": "steel",
    "paper": "paper_board", "corrugated board": "paper_board", "kraft paper": "paper_board",
}
