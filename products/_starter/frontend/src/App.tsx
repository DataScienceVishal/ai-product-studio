import { useCallback, useEffect, useState, type ReactNode } from "react";
import { api, ApiError, SESSION_ENDED, type Me } from "./api";
import { Billing, BillingDone, Dashboard, Help, MockCheckout, MockPortal, Settings } from "./pages/app";
import { Privacy, Terms } from "./pages/legal";
import { ForgotPassword, ResetPassword, safeNext, SignIn, SignUp, VerifyEmail } from "./pages/auth";
import { AcceptInvite, Team } from "./pages/team";
import { Alert, Link, navigate, usePath } from "./ui";

const PUBLIC = new Set(["/login", "/signup", "/forgot-password", "/reset-password", "/accept-invite", "/verify-email", "/help", "/privacy", "/terms"]);

export default function App() {
  const path = usePath();
  const [me, setMe] = useState<Me | null | undefined>(undefined); // undefined = still loading

  const refresh = useCallback(async () => {
    try {
      setMe(await api<Me>("/api/auth/me"));
    } catch (err) {
      if (!(err instanceof ApiError && err.status === 401)) console.warn("couldn't load the session", err);
      setMe(null);
    }
  }, []);
  useEffect(() => { void refresh(); }, [refresh]);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => { // any 401 from the API (expired session, removed member) ends the session here too
    const ended = () => { setMe(null); navigate("/login"); };
    window.addEventListener(SESSION_ENDED, ended);
    return () => window.removeEventListener(SESSION_ENDED, ended);
  }, []);

  useEffect(() => {
    if (me === null && !PUBLIC.has(path)) navigate("/login", true);
  }, [me, path]);

  // Keep in step with SIGN_IN_PAGES in pages/auth.tsx (App.test.tsx checks it). Written as === so test_spa.py can read the routes.
  const signInPage = path === "/login" || path === "/signup";
  useEffect(() => {
    if (me && signInPage) navigate(safeNext(), true); // (honours ?next=) already signed in: the sign-in and sign-up forms have nothing to offer
  }, [me, signInPage]);

  if (me === undefined) return <p className="p-8 text-slate-600">Loading…</p>;
  if (me && signInPage) return null; // one frame only: the effect above replaces the URL, and safeNext() never returns a sign-in page

  if (path === "/signup") return <SignUp onSignedIn={setMe} />;
  if (path === "/login") return <SignIn onSignedIn={setMe} />;
  if (path === "/forgot-password") return <ForgotPassword />;
  if (path === "/reset-password") return <ResetPassword />;
  if (path === "/accept-invite") return <AcceptInvite onSignedIn={setMe} />;
  if (path === "/verify-email") return <VerifyEmail me={me} onVerified={refresh} />;
  if (path === "/privacy" || path === "/terms" || (!me && path === "/help")) {
    return <Shell me={me ?? undefined}>{path === "/privacy" ? <Privacy /> : path === "/terms" ? <Terms /> : <Help />}</Shell>;
  }
  if (!me) return null;

  const signOut = async () => {
    try {
      await api("/api/auth/logout", { method: "POST" });
      setMe(null);
      navigate("/login");
    } catch {
      setNotice("We couldn't sign you out. Check your connection and try again."); // the cookie is still valid
    }
  };

  return (
    <Shell me={me} onSignOut={signOut}>
      {notice && <div className="mb-4"><Alert>{notice}</Alert></div>}
      {path === "/billing" ? <Billing me={me} refresh={refresh} />
        : path === "/billing/done" ? <BillingDone me={me} refresh={refresh} />
        : path === "/billing/mock-checkout" ? <MockCheckout refresh={refresh} />
        : path === "/billing/mock-portal" ? <MockPortal />
        : path === "/settings" ? <Settings me={me} onDeleted={() => setMe(null)} />
        : path === "/team" ? <Team me={me} />
        : path === "/help" ? <Help />
        : path === "/" ? <Dashboard me={me} />
        : <NotFound />}
    </Shell>
  );
}

function NotFound() {
  return (
    <div>
      <h1 className="text-2xl font-bold text-slate-900">Page not found</h1>
      <p className="mt-2 text-slate-600">There is nothing at this address.</p>
      <p className="mt-4"><Link to="/">Go to your notes</Link></p>
    </div>
  );
}

function Shell({ me, onSignOut, children }: { me?: Me; onSignOut?: () => void; children: ReactNode }) {
  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-200 bg-white">
        <nav className="mx-auto flex max-w-4xl flex-wrap items-center gap-4 px-4 py-3" aria-label="Main">
          <Link to="/" className="font-bold text-slate-900">Starter</Link>
          {me && <>
            <Link to="/">Notes</Link>
            <Link to="/team">Team</Link>
            <Link to="/billing">Billing</Link>
            <Link to="/settings">Settings</Link>
          </>}
          <Link to="/help">Help</Link>
          {me && (
            <span className="ml-auto flex items-center gap-3 text-sm text-slate-600">
              {me.tenant.name}
              <button className="rounded-md border border-slate-300 px-3 py-1 hover:bg-slate-100" onClick={onSignOut}>Sign out</button>
            </span>
          )}
        </nav>
      </header>
      <main className="mx-auto max-w-4xl px-4 py-8">{children}</main>
    </div>
  );
}
