
# STATUS (T-190 review fixes)

Done: must-fix 1 (claim check: names must be in the quote, minimum quote size `quote_big_enough`), 2 (DATA.md says evidence deletes are soft),
should-fix 3 (own-sentence marker needed; repeated unmarked sentence flagged), 4 (gate pack state is an allow-list), 6 (0018 downgrade warning).

Board-worthy: **add a purge horizon for soft-deleted evidence documents and their passage text** (today they are kept until account deletion; DATA.md says so).

Left for S7/S8 (reviewer items): 5 (`pack_checked` ignores evidence liveness; a delete during `checking` is not reopened), 7 (extract heading heuristic
can give an imperative-question line the previous question's word window; known limitation), 8 (S7 sign-off and the check route should lock the pack row
`FOR UPDATE`). Also: `hypothesis` is now in the dev extras and requirements-dev.txt (the T-190 line above is out of date).
