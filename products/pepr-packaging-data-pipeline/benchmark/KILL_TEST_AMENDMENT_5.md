# Proposed amendment 5 (NOT applied; for the Studio Lead to decide)

Source: tuning run e08c (results/tuning1, S902). The scorer and truth were not changed.

## Finding
Two S902 values were counted untraced although the model's quotes are on the page and name the right value:
- barrier_layer: quote "no barrier" (page line "tin can - oxygen barrier: monolayer, no barrier"), value "no barrier layer".
- ink_coating: quote "UV-curable ink" (page line "tin can - ink / coating: print: UV-curable ink"), value "UV-cured ink".

`taxonomy.quote_ok` requires the quote to contain a LISTED wording of the value ("monolayer, no barrier", "print: UV-curable ink"). A
sub-span of a listed wording is rejected. Both quotes are verbatim and name no other value, so a human reviewer would call them traced.

## Diagnosis
Not a scorer bug under the letter of the rule (the vocabulary is the contract and the prompt told the model "shortest span"), but the
rule is stricter than the traceability goal. The prompt was changed to ask for the whole printed value, and the extractor now drops a
feature field whose quote fails the test (it scores as a missing slot, not an untraced value).

## Proposal (optional)
Let quote_ok accept a quote that is a contiguous sub-span (whole words) of a listed wording of the value, provided it contains no
listed wording of any other value of the same key. It stays strict on page text (quote must still be on the page).
Risk: shorter quotes such as "none" or "barrier" are ambiguous; guard with "must still name the value" (at least one distinctive word
of the wording, such as "UV-curable" or "no barrier"). Effect on the kill test: untraced count can only fall for correct values; wrong
values still fail the accuracy mark. Recommended: keep the scorer as is (the prompt and the drop rule fix it without weakening the test).

## S904 fabrication (truth is right, no amendment)
Sheet row 2 is "front label | flint green | 1.6 g": no material. The model took PP from item 1's "Decoration label: polypropylene film
label". Truth `missing` is correct. Fixed by a prompt rule (own row only). The page is an image, so no code-side drop applies.
