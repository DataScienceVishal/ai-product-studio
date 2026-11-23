import { useEffect, useRef, useState, type FormEvent } from "react";
import { api, ApiError, type Me } from "../api";
import { Alert, AuthLayout, Button, Field, Link, navigate, takeToken } from "../ui";

/** Where to go after signing in: a same-site path from ?next=, otherwise home. */
export function safeNext(): string {
  const next = new URLSearchParams(window.location.search).get("next") ?? "";
  if (!next.startsWith("/") || next.startsWith("//") || next.includes("\\")) return "/";
  try {
    const url = new URL(next, window.location.origin); // what the browser would actually resolve
    // Dot segments normalise away ("/.//evil" -> "//evil"), which is protocol-relative: refuse that too.
    return url.origin === window.location.origin && !url.pathname.startsWith("//") ? url.pathname + url.search : "/";
  } catch {
    return "/";
  }
}

function useSubmit<T>(action: () => Promise<T>, onDone: (result: T) => void) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      onDone(await action());
    } catch (err) {
      const e = err as ApiError;
      setError(e.fields?.length ? e.fields.map((f) => f.problem).join(" ") : e.message);
    } finally {
      setBusy(false);
    }
  };
  return { busy, error, submit };
}

export function SignUp({ onSignedIn }: { onSignedIn: (me: Me) => void }) {
  const [company, setCompany] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const { busy, error, submit } = useSubmit(
    () => api<Me>("/api/auth/signup", { method: "POST", body: { company_name: company, email, password } }),
    (me) => { onSignedIn(me); navigate("/"); },
  );
  return (
    <AuthLayout title="Start your free trial">
      <form onSubmit={submit} className="space-y-4" noValidate>
        {error && <Alert>{error}</Alert>}
        <Field id="company" label="Company name" value={company} onChange={setCompany} autoComplete="organization" required />
        <Field id="email" label="Work email" type="email" value={email} onChange={setEmail} autoComplete="email" required />
        <Field id="password" label="Password" type="password" value={password} onChange={setPassword}
          autoComplete="new-password" hint="At least 10 characters." required />
        <p className="text-sm text-slate-600">
          By creating an account you agree to the <Link to="/terms">terms</Link> and <Link to="/privacy">privacy notice</Link> (both DRAFT).
        </p>
        <Button type="submit" busy={busy} className="w-full">Create account</Button>
        <p className="text-sm">Already have an account? <Link to="/login">Sign in</Link></p>
      </form>
    </AuthLayout>
  );
}

export function SignIn({ onSignedIn }: { onSignedIn: (me: Me) => void }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const { busy, error, submit } = useSubmit(
    () => api<Me>("/api/auth/login", { method: "POST", body: { email, password } }),
    (me) => { onSignedIn(me); navigate(safeNext()); },
  );
  return (
    <AuthLayout title="Sign in">
      <form onSubmit={submit} className="space-y-4" noValidate>
        {error && <Alert>{error}</Alert>}
        <Field id="email" label="Email" type="email" value={email} onChange={setEmail} autoComplete="email" required />
        <Field id="password" label="Password" type="password" value={password} onChange={setPassword}
          autoComplete="current-password" required />
        <Button type="submit" busy={busy} className="w-full">Sign in</Button>
        <div className="flex justify-between text-sm">
          <Link to="/forgot-password">Forgot your password?</Link>
          <Link to="/signup">Create an account</Link>
        </div>
      </form>
    </AuthLayout>
  );
}

export function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const { busy, error, submit } = useSubmit(
    () => api("/api/auth/password-reset/request", { method: "POST", body: { email } }),
    () => setSent(true),
  );
  return (
    <AuthLayout title="Reset your password">
      {sent ? (
        <Alert kind="success">If that email has an account, we've sent a reset link. It works for 30 minutes.</Alert>
      ) : (
        <form onSubmit={submit} className="space-y-4" noValidate>
          {error && <Alert>{error}</Alert>}
          <Field id="email" label="Email" type="email" value={email} onChange={setEmail} autoComplete="email" required />
          <Button type="submit" busy={busy} className="w-full">Send reset link</Button>
          <p className="text-sm"><Link to="/login">Back to sign in</Link></p>
        </form>
      )}
    </AuthLayout>
  );
}

export function ResetPassword() {
  const [token] = useState(takeToken);
  const [password, setPassword] = useState("");
  const [done, setDone] = useState(false);
  const { busy, error, submit } = useSubmit(
    () => api("/api/auth/password-reset/confirm", { method: "POST", body: { token, new_password: password } }),
    () => setDone(true),
  );
  return (
    <AuthLayout title="Choose a new password">
      {done ? (
        <Alert kind="success">Password changed. <Link to="/login">Sign in</Link> with your new password.</Alert>
      ) : (
        <form onSubmit={submit} className="space-y-4" noValidate>
          {!token && <Alert>This link is incomplete. Ask for a new one from the sign-in page.</Alert>}
          {error && <Alert>{error}</Alert>}
          <Field id="password" label="New password" type="password" value={password} onChange={setPassword}
            autoComplete="new-password" hint="At least 10 characters." required />
          <Button type="submit" busy={busy} disabled={!token} className="w-full">Save new password</Button>
        </form>
      )}
    </AuthLayout>
  );
}

export function VerifyEmail({ me, onVerified }: { me: Me | null; onVerified: () => Promise<void> }) {
  const [token] = useState(takeToken);
  const [state, setState] = useState<"working" | "done" | "failed">("working");
  const [error, setError] = useState<string | null>(null);
  const started = useRef(false); // StrictMode runs effects twice in dev; the link is single-use
  useEffect(() => {
    if (!me || started.current) return; // verifying needs the account the email was sent to
    started.current = true;
    if (!token) { setState("failed"); setError("This link is incomplete."); return; }
    api("/api/auth/verify-email", { method: "POST", body: { token } })
      .then(async () => { setState("done"); await onVerified(); })
      .catch((err: ApiError) => { setState("failed"); setError(err.message); });
  }, [me, token, onVerified]);
  if (!me) {
    const next = encodeURIComponent(`/verify-email?token=${encodeURIComponent(token)}`);
    return (
      <AuthLayout title="Confirm your email">
        <p className="text-slate-700">Sign in to the account this email was sent to, and we'll confirm it straight away.</p>
        <p className="mt-4"><Link to={`/login?next=${next}`}>Sign in to confirm</Link></p>
        <p className="mt-2 text-sm text-slate-600">Didn't sign up? You can ignore the email; nothing happens without your sign-in.</p>
      </AuthLayout>
    );
  }
  return (
    <AuthLayout title="Confirm your email">
      {state === "working" && <p className="text-slate-600">Checking your link…</p>}
      {state === "done" && <Alert kind="success">Thanks, your email is confirmed. <Link to="/">Continue</Link></Alert>}
      {state === "failed" && <Alert>{error}</Alert>}
    </AuthLayout>
  );
}

