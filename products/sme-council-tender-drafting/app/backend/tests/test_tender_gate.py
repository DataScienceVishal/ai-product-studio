"""S6: the pure export gate. A Hypothesis property test over verdict, version, check hash, digest, limit, deleted evidence,
requirement-added and statement-version states, compared with an independent oracle (A6b, R4)."""
from hypothesis import HealthCheck, given, settings, strategies as st

from app.tender import gate
from app.tender.gate import (GateClaim, GateDraft, GatePack, GateReq, GateSignoff, drafts_digest, export_allowed,
                             reason_codes, sha)

VERDICTS = ["supported", "unsupported", "contradicted", "unchecked"]
TEXT = "We hold ISO 9001 certification across all sites [E-3]. Our teams are trained to BICSc standards [E-4]."  # 15 words


def build(s):
    """A pack with two confirmed questions; `s` says which flaws to inject. Returns the gate inputs and the flaw set."""
    reqs = [GateReq("r1", "question", "confirmed", s["limit"]), GateReq("r2", "question", "confirmed", None),
            GateReq("r3", "mandatory", "confirmed", None)]
    drafts, claims = [], []
    for rid in ("r1", "r2"):
        old_text = "An older answer with an unsupported claim [E-3]."
        if s["old_bad"]:  # an older version that was blocked must never matter once a newer one exists
            drafts.append(GateDraft(f"{rid}-v1", rid, 1, old_text, sha(old_text), sha(old_text)))
            claims.append(GateClaim(f"{rid}-v1", "unsupported", (3,)))
        text = TEXT if rid == "r1" else "Another answer with no facts."
        checked = sha(text) if not (s["unchecked_draft"] and rid == "r2") else None
        if s["stale_check"] and rid == "r1":
            checked = sha("some older text")
        drafts.append(GateDraft(f"{rid}-v2", rid, 2, text, sha(text), checked))
        claims.append(GateClaim(f"{rid}-v2", s["verdict"] if rid == "r1" else "supported", (3, 4) if rid == "r1" else ()))
    if s["no_draft"]:
        drafts = [d for d in drafts if d.requirement_id != "r2"]
        claims = [c for c in claims if not c.draft_id.startswith("r2")]
    live = {3, 4} - ({s["deleted"]} if s["deleted"] else set())
    signed_reqs = list(reqs)
    if s["req_added"]:  # a confirmed question was added after the sign-off
        reqs = reqs + [GateReq("r4", "question", "confirmed", None)]
        drafts.append(GateDraft("r4-v1", "r4", 1, "Late answer.", sha("Late answer."), sha("Late answer.")))
        claims.append(GateClaim("r4-v1", "supported", ()))
    signed_drafts = [d for d in drafts if d.requirement_id != "r4"]
    digest = drafts_digest(signed_reqs, signed_drafts)
    if s["digest_bad"]:
        digest = sha("tampered")
    so = None if s["no_signoff"] else GateSignoff("v0" if s["stale_statement"] else gate.STATEMENT_VERSION, digest)
    return GatePack("review" if s["unconfirmed"] else "ready"), reqs, drafts, claims, so, live


STATES = st.fixed_dictionaries({
    "verdict": st.sampled_from(VERDICTS),
    "limit": st.sampled_from([None, 15, 20, 14, 5]),
    "old_bad": st.booleans(), "unchecked_draft": st.booleans(), "stale_check": st.booleans(), "no_draft": st.booleans(),
    "deleted": st.sampled_from([None, 3, 4, 99]), "req_added": st.booleans(), "digest_bad": st.booleans(),
    "no_signoff": st.booleans(), "stale_statement": st.booleans(), "unconfirmed": st.booleans(),
})


def oracle(s) -> set[str]:
    """The reason codes the state must produce, worked out from the flags alone (not from the gate's code)."""
    codes = set()
    if s["verdict"] != "supported":
        codes.add("claims_blocked")
    if s["limit"] is not None and s["limit"] < 15:
        codes.add("over_limit")
    if s["stale_check"] or (s["unchecked_draft"] and not s["no_draft"]):  # r2's draft is gone when no_draft is set
        codes.add("not_checked")
    if s["no_draft"]:
        codes.add("missing_draft")
    if s["deleted"] in (3, 4):
        codes.add("evidence_removed")
    if s["no_signoff"]:
        codes.add("no_signoff")
    else:
        if s["stale_statement"]:
            codes.add("statement_changed")
        if s["digest_bad"] or s["req_added"]:
            codes.add("digest_mismatch")
    if s["unconfirmed"]:
        codes.add("not_confirmed")
    return codes


@settings(max_examples=600, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(STATES)
def test_export_allowed_matches_the_oracle(s):
    pack, reqs, drafts, claims, signoff, live = build(s)
    ok, reasons = export_allowed(pack, reqs, drafts, claims, signoff, live)
    expected = oracle(s)
    assert reason_codes(reasons) == expected, (s, reasons)
    assert ok == (not expected)
    # the old, blocked version never decides anything
    assert "old" not in " ".join(reasons)


@given(STATES)
def test_the_gate_is_deterministic_and_never_mutates_its_inputs(s):
    pack, reqs, drafts, claims, signoff, live = build(s)
    before = (list(reqs), list(drafts), list(claims), set(live))
    a = export_allowed(pack, reqs, drafts, claims, signoff, live)
    b = export_allowed(pack, reqs, drafts, claims, signoff, set(live))
    assert a == b and before == (list(reqs), list(drafts), list(claims), set(live))


def good_state():
    return dict(verdict="supported", limit=None, old_bad=False, unchecked_draft=False, stale_check=False, no_draft=False,
                deleted=None, req_added=False, digest_bad=False, no_signoff=False, stale_statement=False, unconfirmed=False)


def test_the_clean_state_is_allowed_and_every_single_flaw_blocks():
    pack, reqs, drafts, claims, signoff, live = build(good_state())
    assert export_allowed(pack, reqs, drafts, claims, signoff, live) == (True, [])
    for key, bad in [("verdict", "unchecked"), ("verdict", "contradicted"), ("verdict", "unsupported"), ("limit", 5),
                     ("stale_check", True), ("unchecked_draft", True), ("no_draft", True), ("deleted", 3),
                     ("req_added", True), ("digest_bad", True), ("no_signoff", True), ("stale_statement", True)]:
        ok, reasons = export_allowed(*build(good_state() | {key: bad}))
        assert not ok and reasons, (key, bad)


def test_a_limit_lowered_after_sign_off_blocks_even_though_the_snapshot_was_fine():
    pack, reqs, drafts, claims, signoff, live = build(good_state())
    lowered = [GateReq(r.id, r.kind, r.status, 10 if r.id == "r1" else r.word_limit) for r in reqs]
    ok, reasons = export_allowed(pack, lowered, drafts, claims, signoff, live)
    assert not ok and {"over_limit", "digest_mismatch"} <= reason_codes(reasons)  # the limit feeds the digest too


def test_edited_text_with_a_copied_check_hash_is_not_checked():
    pack, reqs, drafts, claims, signoff, live = build(good_state())
    forged = [GateDraft(d.id, d.requirement_id, d.version, d.text + " Extra claim.", d.text_sha256, d.check_sha256)
              if d.id == "r1-v2" else d for d in drafts]
    assert "not_checked" in reason_codes(export_allowed(pack, reqs, forged, claims, signoff, live)[1])


def test_a_marker_in_the_text_for_removed_evidence_blocks_even_without_a_claim_for_it():
    pack, reqs, drafts, claims, signoff, live = build(good_state())
    assert "evidence_removed" in reason_codes(export_allowed(pack, reqs, drafts, [], signoff, live - {4})[1])


def test_no_questions_and_unconfirmed_packs_are_blocked():
    ok, reasons = export_allowed(GatePack("review"), [], [], [], None, set())
    assert not ok and {"not_confirmed", "no_questions", "no_signoff"} <= reason_codes(reasons)
