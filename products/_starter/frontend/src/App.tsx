import { useCallback, useEffect, useState, type ReactNode } from "react";
import { api, ApiError, type Me } from "./api";
import { Billing, Dashboard, Help, MockCheckout, Settings } from "./pages/app";
import { ForgotPassword, ResetPassword, SignIn, SignUp } from "./pages/auth";
import { AcceptInvite, Team } from "./pages/team";
import { Link, navigate, usePath } from "./ui";

const PUBLIC = new Set(["/login", "/signup", "/forgot-password", "/reset-password", "/accept-invite", "/help"]);

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

  useEffect(() => {
    if (me === null && !PUBLIC.has(path)) navigate("/login");
  }, [me, path]);

  if (me === undefined) return <p className="p-8 text-slate-600">Loading…</p>;

  if (path === "/signup") return <SignUp onSignedIn={setMe} />;
  if (path === "/login") return <SignIn onSignedIn={setMe} />;
  if (path === "/forgot-password") return <ForgotPassword />;
  if (path === "/reset-password") return <ResetPassword />;
  if (path === "/accept-invite") return <AcceptInvite onSignedIn={setMe} />;
  if (!me) return path === "/help" ? <Shell><Help /></Shell> : null;

  const signOut = async () => {
    await api("/api/auth/logout", { method: "POST" }).catch(() => undefined);
    setMe(null);
    navigate("/login");
  };

  return (
    <Shell me={me} onSignOut={signOut}>
      {path === "/billing" ? <Billing me={me} refresh={refresh} />
        : path === "/billing/mock-checkout" ? <MockCheckout refresh={refresh} />
        : path === "/settings" ? <Settings me={me} onDeleted={() => setMe(null)} />
        : path === "/team" ? <Team me={me} />
        : path === "/help" ? <Help />
        : <Dashboard me={me} />}
    </Shell>
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
