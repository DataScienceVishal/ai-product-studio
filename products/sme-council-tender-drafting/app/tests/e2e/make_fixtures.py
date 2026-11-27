"""Writes the small e2e fixtures into the directory given as argv[1]: a tender DOCX and an evidence text file.
Run with the backend's python (needs python-docx)."""
import sys
from pathlib import Path

import docx

out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)
d = docx.Document()
d.add_paragraph("Invitation to Tender: Grounds maintenance for Northfield Council", style="Heading 1")
d.add_paragraph("1. Describe your safeguarding policy and staff training for grounds maintenance. Maximum of 150 words.")
d.add_paragraph("2. Describe your environmental and social value commitments for grounds maintenance. Maximum of 150 words.")
d.save(out / "tender.docx")
# One passage per file, no full stop, and no word shared between the two topics: ScriptedFakeAI drafts the first sentence of each
# retrieved passage and the claim check needs one clean sentence per draft, so a trailing full stop or a second passage breaks the pairing.
(out / "evidence1.txt").write_text(
    "Our safeguarding policy staff was approved in 2025 and all 42 staff complete safeguarding "
    "training every year", encoding="utf-8")
(out / "evidence2.txt").write_text(
    "Our environmental and social value commitments include 12 apprenticeships and recycling "
    "90 percent of green waste", encoding="utf-8")
