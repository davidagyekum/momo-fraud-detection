import {
  ChevronLeft,
  ChevronRight,
  LogOut,
  Menu,
  MonitorCog,
  UserRound,
} from "lucide-react";
import { useMemo, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/use-auth";
import { BrandMark } from "../components/brand-mark";
import { Dialog, Drawer } from "../components/overlays";
import { Button } from "../components/primitives";
import { appConfig } from "../lib/config";
import {
  portalRoutes,
  profileRoute,
  routeForPath,
  type PortalRoute,
} from "./routes";

function primaryRole(roles: string[]): string {
  if (roles.includes("ADMIN")) return "Administrator";
  if (roles.includes("INVESTIGATOR")) return "Investigator";
  return "No staff role";
}

function NavigationItems({
  routes,
  onSelect,
}: {
  routes: PortalRoute[];
  onSelect?: () => void;
}) {
  return (
    <nav className="side-navigation" aria-label="Staff portal">
      {routes.map((route) => {
        const Icon = route.icon;
        return (
          <NavLink
            key={route.path}
            to={route.path}
            onClick={onSelect}
            className={({ isActive }) =>
              isActive
                ? "side-navigation__link active"
                : "side-navigation__link"
            }
          >
            <Icon size={20} strokeWidth={1.75} aria-hidden="true" />
            <span>{route.label}</span>
          </NavLink>
        );
      })}
    </nav>
  );
}

export function AppShell(): React.ReactNode {
  const auth = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const [logoutOpen, setLogoutOpen] = useState(false);
  const [logoutBusy, setLogoutBusy] = useState(false);

  const allowedRoutes = useMemo(
    () =>
      portalRoutes.filter((route) =>
        auth.user?.roles.some((role) => route.roles.includes(role)),
      ),
    [auth.user?.roles],
  );
  const currentRoute = routeForPath(location.pathname);
  const role = primaryRole(auth.user?.roles ?? []);
  const initials = (auth.user?.full_name ?? "Staff member")
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("");

  const signOut = async (): Promise<void> => {
    setLogoutBusy(true);
    try {
      await auth.signOut();
      void navigate("/login", { replace: true });
    } finally {
      setLogoutBusy(false);
      setLogoutOpen(false);
    }
  };

  return (
    <div className={`app-shell ${collapsed ? "app-shell--collapsed" : ""}`}>
      <a className="skip-link" href="#main-content">
        Skip to main content
      </a>
      <aside className="app-sidebar">
        <div className="app-sidebar__brand">
          <BrandMark compact={collapsed} />
          <Button
            variant="ghost"
            className="app-sidebar__collapse"
            aria-label={collapsed ? "Expand navigation" : "Collapse navigation"}
            aria-expanded={!collapsed}
            icon={collapsed ? <ChevronRight /> : <ChevronLeft />}
            onClick={() => setCollapsed((value) => !value)}
          >
            {collapsed ? "Expand" : "Collapse"}
          </Button>
        </div>
        <NavigationItems routes={allowedRoutes} />
        <div className="app-sidebar__context">
          <div>
            <MonitorCog size={19} aria-hidden="true" />
            <span>
              <small>Environment</small>
              <strong>{appConfig.environment}</strong>
            </span>
          </div>
          <div>
            <UserRound size={19} aria-hidden="true" />
            <span>
              <small>Current role</small>
              <strong>{role}</strong>
            </span>
          </div>
        </div>
      </aside>

      <header className="app-header">
        <Button
          variant="ghost"
          className="app-header__menu"
          aria-label="Open navigation"
          aria-expanded={drawerOpen}
          icon={<Menu />}
          onClick={() => setDrawerOpen(true)}
        >
          Menu
        </Button>
        <div className="app-header__crumb" aria-label="Breadcrumb">
          <span aria-hidden="true">/</span>
          <span>{currentRoute?.label ?? "Portal"}</span>
        </div>
        <div className="app-header__context">
          <span>{appConfig.environment}</span>
          <span>{role}</span>
          <NavLink
            to={profileRoute.path}
            className="profile-link"
            aria-label="Open profile and security"
          >
            {initials || "SM"}
          </NavLink>
        </div>
      </header>

      <main id="main-content" className="app-main" tabIndex={-1}>
        <Outlet />
      </main>

      <Drawer
        open={drawerOpen}
        title="Navigation"
        onClose={() => setDrawerOpen(false)}
      >
        <div className="drawer-brand">
          <BrandMark />
          <p>
            {appConfig.environment} · {role}
          </p>
        </div>
        <NavigationItems
          routes={allowedRoutes}
          onSelect={() => setDrawerOpen(false)}
        />
        <NavLink
          to={profileRoute.path}
          onClick={() => setDrawerOpen(false)}
          className="drawer-profile-link"
        >
          <UserRound size={20} /> Profile / Security
        </NavLink>
        <Button
          variant="secondary"
          icon={<LogOut />}
          onClick={() => setLogoutOpen(true)}
        >
          Sign out
        </Button>
      </Drawer>

      <Dialog
        open={logoutOpen}
        title="Sign out of the staff portal?"
        onClose={() => setLogoutOpen(false)}
        footer={
          <>
            <Button variant="ghost" onClick={() => setLogoutOpen(false)}>
              Stay signed in
            </Button>
            <Button
              variant="danger"
              loading={logoutBusy}
              onClick={() => void signOut()}
            >
              Sign out
            </Button>
          </>
        }
      >
        <p>
          Your current refresh session will be revoked and protected portal data
          will be cleared.
        </p>
      </Dialog>
    </div>
  );
}
