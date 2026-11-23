import { useCallback, useEffect, useState, type FormEvent } from "react";
import { api, ApiError, type Me } from "../api";
import { Alert, AuthLayout, Button, Card, Field, navigate } from "../ui";

type Member = { id: string; email: string; role: string; created_at: string };
type Invitation = { id: string; email: string; expires_at: string };
type TeamData = { members: Member[]; invitations?: Invitation[] };

const message = (err: unknown) => (err instanceof ApiError ? err.message : "Something went wrong.");

export function Team({ me }: { me: Me }) {
  const [team, setTeam] = useState<TeamData | null>(null);
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const isOwner = me.user.role === "owner";

  const load = useCallback(async () => {
    try {
      setTeam(await api<TeamData>("/api/team"));
    } catch (err) {
      setError(message(err));
    }
  }, []);
  useEffect(() => { void load(); }, [load]);

  const act = async (key: string, action: () => Promise<unknown>, done?: string) => {
    setBusy(key);
    setError(null);
    setNotice(null);
    try {
      await action();
      if (done) setNotice(done);
      await load();
    } catch (err) {
      setError(message(err));
    } finally {
      setBusy(null);
    }
  };

  const invite = (event: FormEvent) => {
    event.preventDefault();
    void act("invite", async () => {
      await api("/api/team/invitations", { method: "POST", body: { email } });
      setEmail("");
    }, `Invitation sent to ${email}. The link works for 7 days.`);
  };

  return (
    <div className="space-y-6">
      {error && <Alert>{error}</Alert>}
      {notice && <Alert kind="success">{notice}</Alert>}
      <Card title="Team">
        {team === null ? <p className="text-slate-600">Loading…</p> : (
          <ul className="divide-y divide-slate-200">
            {team.members.map((member) => (
              <li key={member.id} className="flex items-center justify-between py-3">
                <span>{member.email} <span className="text-sm text-slate-600">({member.role})</span></span>
                {isOwner && member.id !== me.user.id && (
                  <Button variant="secondary" busy={busy === member.id} aria-label={`Remove ${member.email}`}
                    onClick={() => act(member.id, () => api(`/api/team/members/${member.id}`, { method: "DELETE" }),
                      `${member.email} was removed and signed out.`)}>Remove</Button>
                )}
              </li>
            ))}
          </ul>
        )}
      </Card>
      {isOwner && (
        <>
          <Card title="Invite someone">
            <form onSubmit={invite} className="flex flex-col gap-3 sm:flex-row sm:items-end">
              <div className="grow">
                <Field id="invite-email" label="Their work email" type="email" value={email} onChange={setEmail} required />
              </div>
              <Button type="submit" busy={busy === "invite"} disabled={!email.trim()}>Send invitation</Button>
            </form>
            <p className="mt-2 text-sm text-slate-600">Members can use everything except billing, data export and deleting the account.</p>
          </Card>
          {team?.invitations && team.invitations.length > 0 && (
            <Card title="Waiting to accept">
              <ul className="divide-y divide-slate-200">
                {team.invitations.map((inv) => (
                  <li key={inv.id} className="flex items-center justify-between py-3">
                    <span>{inv.email} <span className="text-sm text-slate-600">(expires {new Date(inv.expires_at).toLocaleDateString("en-GB")})</span></span>
                    <Button variant="secondary" busy={busy === inv.id} aria-label={`Cancel invitation for ${inv.email}`}
                      onClick={() => act(inv.id, () => api(`/api/team/invitations/${inv.id}`, { method: "DELETE" }))}>Cancel</Button>
                  </li>
                ))}
              </ul>
            </Card>
          )}
        </>
      )}
    </div>
  );
}

export function AcceptInvite({ onSignedIn }: { onSignedIn: (me: Me) => void }) {
  const token = new URLSearchParams(window.location.search).get("token") ?? "";
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const me = await api<Me>("/api/invitations/accept", { method: "POST", body: { token, password } });
      onSignedIn(me);
      navigate("/");
    } catch (err) {
      setError(message(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthLayout title="Join your team">
      <form onSubmit={submit} className="space-y-4" noValidate>
        {!token && <Alert>This invitation link is incomplete. Ask whoever invited you to send it again.</Alert>}
        {error && <Alert>{error}</Alert>}
        <Field id="password" label="Choose a password" type="password" value={password} onChange={setPassword}
          autoComplete="new-password" hint="At least 10 characters." required />
        <Button type="submit" busy={busy} disabled={!token} className="w-full">Join</Button>
      </form>
    </AuthLayout>
  );
}
