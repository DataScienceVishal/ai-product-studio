"""Writes the e2e fixtures into the directory given as argv[1]: a tender DOCX and evidence text files for the core flow, plus
the subfolders limits/, unicode/ and large/ for the other scenarios. Run with the backend's python (needs python-docx)."""
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

# ---- limits (tender_limits.cjs): one answered question, one with no evidence (gap marker), one over its word limit ----
lim = out / "limits"
lim.mkdir(exist_ok=True)
d = docx.Document()
d.add_paragraph("Invitation to Tender: Grounds maintenance for Northfield Council", style="Heading 1")
d.add_paragraph("1. Describe your safeguarding policy and staff training for grounds maintenance. Maximum of 150 words.")
d.add_paragraph("2. Describe your approach to fleet vehicle emissions. Maximum of 40 words.")
d.add_paragraph("3. Describe your health and safety induction record. Maximum of 10 words.")
d.save(lim / "tender.docx")
(lim / "evidence1.txt").write_text(
    "Our safeguarding policy staff was approved in 2025 and all 42 staff complete safeguarding "
    "training every year", encoding="utf-8")
(lim / "evidence3.txt").write_text(
    "Our health and safety induction record shows that every operative completes a full accredited induction course "
    "before starting any work on a council site", encoding="utf-8")

# ---- unicode (tender_unicode.cjs): curly quotes, accents, pound sign, en dash ----
uni = out / "unicode"
uni.mkdir(exist_ok=True)
d = docx.Document()
d.add_paragraph("Invitation to Tender: Grounds maintenance for the Café Quarter – Northfield Council", style="Heading 1")
d.add_paragraph("1. Describe your safeguarding arrangements for the “Zoë Café” contract – worth up to £2m. Maximum of 150 words.")
d.add_paragraph("2. Describe your social value pledge for local charities – Maximum of 150 words.")
d.save(uni / "tender.docx")
(uni / "evidence1.txt").write_text(
    "Our safeguarding lead Zoë O’Brien–Núñez has held the role since 2021 and the “Zoë Café” contract is worth £1,250,000 a year",
    encoding="utf-8")
(uni / "evidence2.txt").write_text(
    "Our social value pledge – £75,000 a year for local charities – supports the “Aroma Bär” training venue in Besançon Road",
    encoding="utf-8")

# ---- large (tender_unicode.cjs, second scenario): 8 questions over 4 pages, 8 evidence files ----
big = out / "large"
big.mkdir(exist_ok=True)
topics = ["beekeeping", "irrigation", "pesticide", "hedgerow", "drainage", "playground", "signage", "composting"]
d = docx.Document()
d.add_paragraph("Invitation to Tender: Grounds maintenance for Northfield Council", style="Heading 1")
for i, topic in enumerate(topics, start=1):
    d.add_paragraph(f"{i}. Describe your approach to {topic}. Maximum of {100 + 10 * i} words.")
    d.add_paragraph("Bidders should write in plain English and give evidence for every claim. " * 12)
    if i % 2 == 0 and i < len(topics):
        d.add_page_break()
d.save(big / "tender.docx")
for i, topic in enumerate(topics, start=1):
    (big / f"evidence{i}.txt").write_text(
        f"Our {topic} work was reviewed in 2025 and covers {10 + i * 7} sites", encoding="utf-8")
