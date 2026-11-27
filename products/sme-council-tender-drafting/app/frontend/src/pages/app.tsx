import { useEffect, useState, type FormEvent } from "react";
import { api, ApiError, formatPrice, isBillingEnabled, isMockBilling, type AiAllowance, type Me, type Plan } from "../api";
import { Alert, Button, Card, Field, Link, navigate } from "../ui";
import { BAD_REDIRECT, safeRedirect } from "../redirect";

function errorText(err: unknown) {
  return err instanceof ApiError ? err.message : "Something went wrong.";
}

export function Dashboard({ me }: { me: Me }) {
  return (
    <div className="space-y-6">
      <VerifyBanner me={me} />
      <TrialBanner me={me} />
      <Card title="Tender packs">
        <p className="text-slate-700">Your tender packs will appear here. Upload a council tender pack to start a draft.</p>
      </Card>
    </div>
  );
}

function VerifyBanner({ me }: { me: Me }) {
  const [sent, setSent] = useState<string | null>(null);
  if (me.user.email_verified) return null;
  const resend = async () => {
    try {
      setSent((await api<{ status: string }>("/api/auth/verify-email/resend", { method: "POST" })).status);
    } catch (err) {
      setSent(errorText(err));
    }
  };
  return (
    <Alert kind="info">
      Please confirm your email address: we sent you a link. {sent ?? <button className="underline" onClick={resend}>Send it again</button>}
    </Alert>
  );
}

function TrialBanner({ me }: { me: Me }) {
  const { status, trial_ends_at: ends } = me.subscription;
  if (status !== "trialing" || !ends || !isBillingEnabled()) return null;  // billing off: the trial does not lapse
  const days = Math.max(0, Math.ceil((new Date(ends).getTime() - Date.now()) / 86_400_000));
  return (
    <Alert kind="info">
      Free trial: {days} day{days === 1 ? "" : "s"} left. <Link to="/billing">Choose a plan</Link> any time.
    </Alert>
  );
}

/** The mock provider's portal page is part of the SPA: return its path + query when the URL points there, else null. */
function mockPortalPath(url: string): string | null {
  try {
    const target = new URL(url, window.location.origin);
    // Only http(s): a javascript:/data:/blob: URL must not be mistaken for the portal, so safeRedirect refuses it.
    if (target.protocol !== "http:" && target.protocol !== "https:") return null;
    return target.pathname === "/billing/mock-portal" ? target.pathname + target.search : null;
  } catch {
    return null;
  }
}

export function Billing({ me, refresh }: { me: Me; refresh: () => Promise<void> }) {
  const [plans, setPlans] = useState<Plan[]>([]);
  const [allowance, setAllowance] = useState<AiAllowance | null>(null);
  const [offer, setOffer] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [portalBusy, setPortalBusy] = useState(false);
  const isOwner = me.user.role === "owner";
  useEffect(() => {
    api<{ plans: Plan[]; ai_allowance?: AiAllowance }>("/api/billing/plans").then((r) => {
      setPlans(r.plans);
      setAllowance(r.ai_allowance ?? null);
    }).catch((e) => setError(errorText(e)));
  }, []);

  const choose = async (plan: string) => {
    setBusy(plan);
    setError(null);
    try {
      const checkout = await api<{ checkout_id: string; url: string }>("/api/billing/checkout",
        { method: "POST", body: { plan, offer_code: offer || null } });
      if (checkout.checkout_id.startsWith("mock_")) {
        navigate(`/billing/mock-checkout?session=${encodeURIComponent(checkout.checkout_id)}`);
      } else {
        if (!safeRedirect(checkout.url)) setError(BAD_REDIRECT);
      }
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(null);
    }
  };

  // Same rule as the server's verified_owner gate: only blocked when verification is required AND the owner is unverified.
  const blocked = me.user.email_verification_required && !me.user.email_verified;
  const openPortal = async () => {
    setPortalBusy(true);
    setError(null);
    try {
      const portal = await api<{ url: string }>("/api/billing/portal", { method: "POST" });
      const inApp = mockPortalPath(portal.url);
      if (inApp) {
        navigate(inApp);  // like mock checkout: stay in the SPA, whatever origin it is served from
        setPortalBusy(false);
      } else if (!safeRedirect(portal.url)) {
        setError(BAD_REDIRECT);
        setPortalBusy(false);
      }
    } catch (err) {
      setError(errorText(err));
      setPortalBusy(false);  // on success the page navigates away, so the button stays disabled until then
    }
  };

  return (
    <div className="space-y-6">
      <Card title="Your plan">
        <p>Plan: <strong>{me.subscription.plan}</strong> · Status: <strong>{me.subscription.status}</strong>
          {me.subscription.offer && <> · Offer: <strong>{me.subscription.offer}</strong></>}</p>
        {me.subscription.status === "past_due" && (
          <Alert kind="info">Your last payment failed. {isOwner ? 'Choose "Manage billing" below to update your card.'
            : "Ask the account owner to update the card under Billing."}</Alert>
        )}
        <div className="mt-3 flex flex-wrap gap-2">
          <Button variant="secondary" onClick={() => void refresh()}>Refresh</Button>
          {isOwner && <Button variant="secondary" busy={portalBusy} disabled={blocked}
            onClick={() => void openPortal()}>Manage billing</Button>}
          {isOwner && blocked && <span className="self-center text-sm text-slate-600">Verify your email to manage billing</span>}
        </div>
      </Card>
      {error && <Alert>{error}</Alert>}
      <Card title="Plans">
        <div className="mb-4 max-w-xs">
          <Field id="offer" label="Offer code (optional)" value={offer} onChange={setOffer} hint="Early customers: EARLY50" />
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          {plans.map((plan) => (
            <div key={plan.id} className="rounded-md border border-slate-200 p-4">
              <h3 className="font-semibold">{plan.name}</h3>
              <p className="text-2xl font-bold">{formatPrice(plan.price_pence, plan.currency)}<span className="text-sm font-normal"> / {plan.interval}</span></p>
              <p className="text-sm text-slate-600">{plan.ai_monthly_tokens.toLocaleString("en-GB")} AI tokens a month
                {allowance?.trial_sized && " once live billing starts"}</p>
              <Button className="mt-3" busy={busy === plan.id} onClick={() => choose(plan.id)}
                disabled={!isOwner || blocked}>Choose {plan.name}</Button>
            </div>
          ))}
        </div>
        <p className="mt-4 text-sm text-slate-600">Test mode: no real payment is taken.</p>
        {allowance?.trial_sized && (
          <p className="mt-1 text-sm text-slate-600" data-testid="trial-sized-allowance">
            While billing is in test mode, every plan uses the free-trial AI allowance:{" "}
            {allowance.monthly_tokens.toLocaleString("en-GB")} tokens a month
            {allowance.daily_tokens != null && <> and {allowance.daily_tokens.toLocaleString("en-GB")} a day</>}.</p>
        )}
      </Card>
    </div>
  );
}

export function MockCheckout({ refresh }: { refresh: () => Promise<void> }) {
  const session = new URLSearchParams(window.location.search).get("session") ?? "";
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const pay = async () => {
    setBusy(true);
    try {
      await api(`/api/billing/mock/complete/${encodeURIComponent(session)}`, { method: "POST" });
      await refresh();
      navigate("/billing");
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  };
  return (
    <Card title="Test checkout">
      <p className="mb-4 text-slate-700">This is the mock payment page used in demos. Nothing is charged.</p>
      {error && <Alert>{error}</Alert>}
      <div className="flex gap-2">
        <Button busy={busy} onClick={pay}>Pay (test)</Button>
        <Button variant="secondary" onClick={() => navigate("/billing")}>Cancel</Button>
      </div>
    </Card>
  );
}

export function MockPortal() {
  if (!isMockBilling()) {
    return <Card title="Page not found"><p className="mb-4 text-slate-700">There is nothing here.</p><Link to="/billing">Back to billing</Link></Card>;
  }
  const customer = new URLSearchParams(window.location.search).get("customer") ?? "";
  return (
    <Card title="Mock billing portal">
      <p className="mb-2 text-slate-700">This is the mock billing portal used in demos and development. With Stripe, the real customer portal opens here instead.</p>
      <p className="mb-4 text-sm text-slate-600">Customer ref: <code>{customer || "(none)"}</code></p>
      <Link to="/billing">Back to billing</Link>
    </Card>
  );
}

export function Settings({ me, onDeleted }: { me: Me; onDeleted: () => void }) {
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const download = async () => {
    try {
      const data = await api("/api/account/export");
      const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }));
      const link = Object.assign(document.createElement("a"), { href: url, download: "my-data.json" });
      link.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(errorText(err));
    }
  };

  const remove = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api("/api/account", { method: "DELETE", body: { password, confirm } });
      onDeleted();
      navigate("/signup");
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  };

  if (me.user.role !== "owner") return <MemberSettings onDeleted={onDeleted} />;
  return (
    <div className="space-y-6">
      {error && <Alert>{error}</Alert>}
      <Card title="Your data">
        <p className="mb-3 text-slate-700">Download everything your company has stored here as a JSON file.</p>
        <Button variant="secondary" onClick={download}>Download my data</Button>
      </Card>
      <Card title="Delete account">
        <form onSubmit={remove} className="space-y-4">
          <p className="text-slate-700">This permanently deletes <strong>{me.tenant.name}</strong>, every user and all data. It can't be undone.</p>
          <Field id="delete-password" label="Your password" type="password" value={password} onChange={setPassword} autoComplete="current-password" required />
          <Field id="delete-confirm" label='Type DELETE to confirm' value={confirm} onChange={setConfirm} required />
          <Button type="submit" variant="danger" busy={busy} disabled={confirm !== "DELETE" || !password}>Delete everything</Button>
        </form>
      </Card>
    </div>
  );
}

function MemberSettings({ onDeleted }: { onDeleted: () => void }) {
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const download = async () => {
    try {
      const data = await api("/api/account/me/export");
      const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }));
      Object.assign(document.createElement("a"), { href: url, download: "my-data.json" }).click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(errorText(err));
    }
  };
  const leave = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api("/api/account/me", { method: "DELETE", body: { password, confirm } });
      onDeleted();
      navigate("/login");
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="space-y-6">
      {error && <Alert>{error}</Alert>}
      <Card title="Your data">
        <p className="mb-3 text-slate-700">Download your profile. Billing and company settings belong to the account owner.</p>
        <Button variant="secondary" onClick={download}>Download my data</Button>
      </Card>
      <Card title="Leave this team">
        <form onSubmit={leave} className="space-y-4">
          <p className="text-slate-700">This deletes your sign-in. What you created stays with the company.</p>
          <Field id="leave-password" label="Your password" type="password" value={password} onChange={setPassword} autoComplete="current-password" required />
          <Field id="leave-confirm" label="Type DELETE to confirm" value={confirm} onChange={setConfirm} required />
          <Button type="submit" variant="danger" busy={busy} disabled={confirm !== "DELETE" || !password}>Leave and delete my sign-in</Button>
        </form>
      </Card>
    </div>
  );
}

export function BillingDone({ refresh, me }: { refresh: () => Promise<void>; me: Me }) {
  const [waited, setWaited] = useState(0);
  const active = me.subscription.status === "active";
  useEffect(() => {
    if (active || waited >= 15) return;
    const timer = setTimeout(async () => { await refresh(); setWaited((w) => w + 1); }, 2000);
    return () => clearTimeout(timer);
  }, [active, waited, refresh]);
  return (
    <Card title="Payment">
      {active ? <Alert kind="success">You're on the {me.subscription.plan} plan. Thank you!</Alert>
        : waited >= 15 ? <Alert>We haven't had confirmation from the payment provider yet. Check Billing again in a few minutes.</Alert>
        : <p className="text-slate-700">Confirming your payment…</p>}
      <p className="mt-4"><Link to="/">Back to your tender packs</Link></p>
    </Card>
  );
}

export function Help() {
  const faqs = [
    ["Is my data shared with other companies?", "No. Each company's data is kept separate, and other customers can't see it."],
    ["What does the AI see?", "Only the tender documents and evidence you give it for a draft. It is sent to Microsoft's Azure OpenAI service, which processes it under Microsoft's data-protection terms: Microsoft may store prompts and answers for abuse monitoring, as described on its Azure OpenAI data-privacy page, and some deployment types process data outside the UK and EU. Other customers never see it."],
    ["How do I delete my data?", "You can delete your account and all its data from Settings at any time."],
  ];
  return (
    <Card title="Help">
      <dl className="space-y-4">
        {faqs.map(([q, a]) => (
          <div key={q}>
            <dt className="font-semibold">{q}</dt>
            <dd className="text-slate-700">{a}</dd>
          </div>
        ))}
      </dl>
    </Card>
  );
}
