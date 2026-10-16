import { Suspense, useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { Logo } from "./Logo";
import { LoadingState } from "./States";

const NAV = [
  { to: "/app", label: "Overview", end: true },
  { to: "/app/resume", label: "My resume" },
  { to: "/app/preferences", label: "Preferences" },
  { to: "/app/matches", label: "Recommended jobs" },
  { to: "/app/jobs", label: "Find jobs" },
  { to: "/app/skills", label: "Skill gaps" },
  { to: "/app/saved", label: "Saved jobs" },
  { to: "/app/history", label: "Search history" },
  { to: "/app/evaluation", label: "Model evaluation" },
  { to: "/app/settings", label: "Settings & privacy" },
];

export function AppShell() {
  const { profile, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const location = useLocation();
  useEffect(() => setOpen(false), [location.pathname]);

  const nav = (
    <nav aria-label="Main">
      <ul className="space-y-0.5">
        {NAV.map((item) => (
          <li key={item.to}>
            <NavLink
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `flex min-h-10 items-center rounded px-3 py-2 text-sm no-underline max-lg:min-h-11 pointer-coarse:min-h-11 ${isActive ? "bg-teal-tint font-semibold text-teal-dark" : "text-ink hover:bg-paper"}`
              }
            >
              {item.label}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  );

  return (
    <div className="min-h-screen lg:flex">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded focus:bg-surface focus:px-3 focus:py-2">
        Skip to content
      </a>
      <aside className="sticky top-0 hidden h-screen w-64 shrink-0 flex-col overflow-y-auto border-r border-line bg-surface px-4 py-6 lg:flex">
        <Link to="/app" className="no-underline">
          <Logo className="px-3" />
        </Link>
        <div className="mt-8 flex-1">{nav}</div>
        <div className="border-t border-line px-3 pt-4 text-sm">
          <p className="truncate text-muted" title={profile?.user.email}>
            {profile?.user.email}
          </p>
          <button type="button" onClick={logout} className="mt-1 min-h-10 text-teal underline-offset-2 hover:underline pointer-coarse:min-h-11">
            Sign out
          </button>
        </div>
      </aside>
      <header className="sticky top-0 z-30 flex items-center justify-between gap-3 border-b border-line bg-surface px-4 py-2 sm:px-6 lg:hidden">
        <Link to="/app" className="no-underline">
          <Logo />
        </Link>
        <button type="button" className="btn-secondary" aria-expanded={open} aria-controls="mobile-nav" onClick={() => setOpen((v) => !v)}>
          {open ? "Close" : "Menu"}
        </button>
      </header>
      {open && (
        <div
          id="mobile-nav"
          className="sticky top-[3.75rem] z-20 max-h-[calc(100dvh-3.75rem)] overflow-y-auto border-b border-line bg-surface px-4 py-3 shadow-sm sm:px-6 lg:hidden"
        >
          {nav}
          <div className="mt-3 border-t border-line px-3 pt-3 text-sm">
            <p className="truncate text-muted">{profile?.user.email}</p>
            <button type="button" onClick={logout} className="mt-1 min-h-11 text-teal">
              Sign out
            </button>
          </div>
        </div>
      )}
      <main id="main" className="min-w-0 flex-1 px-4 py-6 sm:px-6 md:px-8 md:py-8 lg:px-10 lg:py-10">
        <div className="mx-auto max-w-6xl">
          <Suspense fallback={<LoadingState />}>
            <Outlet />
          </Suspense>
        </div>
      </main>
    </div>
  );
}

export function PageHeader({ title, description, actions }: { title: string; description?: string; actions?: React.ReactNode }) {
  return (
    <div className="mb-8 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
      <div>
        <h1 className="text-2xl font-bold md:text-3xl">{title}</h1>
        {description && <p className="mt-2 max-w-prose text-muted">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </div>
  );
}
