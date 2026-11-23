import { useEffect, useState, type ButtonHTMLAttributes, type ReactNode } from "react";

// --- tiny history router (no dependency) ---------------------------------------------------

export function navigate(to: string) {
  window.history.pushState({}, "", to);
  window.dispatchEvent(new PopStateEvent("popstate"));
}

export function usePath(): string {
  const [path, setPath] = useState(window.location.pathname);
  useEffect(() => {
    const onChange = () => setPath(window.location.pathname);
    window.addEventListener("popstate", onChange);
    return () => window.removeEventListener("popstate", onChange);
  }, []);
  return path;
}

export function Link({ to, children, className }: { to: string; children: ReactNode; className?: string }) {
  return (
    <a
      href={to}
      className={className ?? "text-blue-700 underline-offset-2 hover:underline"}
      onClick={(event) => {
        if (event.metaKey || event.ctrlKey || event.shiftKey || event.button !== 0) return;
        event.preventDefault();
        navigate(to);
      }}
    >
      {children}
    </a>
  );
}

// --- building blocks -------------------------------------------------------------------------

export function Field(props: {
  id: string; label: string; type?: string; value: string; onChange: (value: string) => void;
  autoComplete?: string; required?: boolean; hint?: string; multiline?: boolean;
}) {
  const common = "mt-1 block w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-slate-900 shadow-sm focus:border-blue-600";
  return (
    <div>
      <label htmlFor={props.id} className="block text-sm font-medium text-slate-800">{props.label}</label>
      {props.multiline ? (
        <textarea id={props.id} className={`${common} min-h-32`} value={props.value} required={props.required}
          onChange={(e) => props.onChange(e.target.value)} />
      ) : (
        <input id={props.id} className={common} type={props.type ?? "text"} value={props.value} required={props.required}
          autoComplete={props.autoComplete} onChange={(e) => props.onChange(e.target.value)}
          aria-describedby={props.hint ? `${props.id}-hint` : undefined} />
      )}
      {props.hint && <p id={`${props.id}-hint`} className="mt-1 text-sm text-slate-600">{props.hint}</p>}
    </div>
  );
}

export function Button({ children, busy, variant = "primary", ...rest }: {
  children: ReactNode; busy?: boolean; variant?: "primary" | "secondary" | "danger";
} & ButtonHTMLAttributes<HTMLButtonElement>) {
  const styles = {
    primary: "bg-blue-700 text-white hover:bg-blue-800",
    secondary: "bg-white text-slate-900 border border-slate-300 hover:bg-slate-100",
    danger: "bg-red-700 text-white hover:bg-red-800",
  }[variant];
  return (
    <button {...rest} disabled={busy || rest.disabled}
      className={`inline-flex items-center justify-center rounded-md px-4 py-2 text-sm font-semibold disabled:opacity-60 ${styles} ${rest.className ?? ""}`}>
      {busy ? "Working…" : children}
    </button>
  );
}

export function Alert({ kind = "error", children }: { kind?: "error" | "info" | "success"; children: ReactNode }) {
  const styles = { error: "bg-red-50 text-red-900 border-red-200", info: "bg-blue-50 text-blue-900 border-blue-200",
    success: "bg-green-50 text-green-900 border-green-200" }[kind];
  return <div role={kind === "error" ? "alert" : "status"} className={`rounded-md border px-4 py-3 text-sm ${styles}`}>{children}</div>;
}

export function Card({ title, children }: { title?: string; children: ReactNode }) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
      {title && <h2 className="mb-4 text-lg font-semibold">{title}</h2>}
      {children}
    </section>
  );
}

export function AuthLayout({ title, children }: { title: string; children: ReactNode }) {
  return (
    <main className="mx-auto mt-16 max-w-md px-4">
      <h1 className="mb-6 text-2xl font-bold">{title}</h1>
      <Card>{children}</Card>
    </main>
  );
}
