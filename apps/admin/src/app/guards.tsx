import type { PropsWithChildren } from "react";
import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../auth/use-auth";
import { Skeleton } from "../components/feedback";
import type { Role } from "../types/api";

const staffRoles = new Set<Role>(["ADMIN", "INVESTIGATOR"]);

export function SessionGate(): React.ReactNode {
  const auth = useAuth();
  const location = useLocation();
  if (auth.phase === "restoring") {
    return (
      <main className="session-gate" aria-busy="true">
        <span className="session-gate__brand">MoMo-FDVS</span>
        <Skeleton lines={2} label="Restoring staff session" />
      </main>
    );
  }
  if (auth.phase === "anonymous" || auth.phase === "expired") {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  }
  if (!auth.user?.roles.some((role) => staffRoles.has(role))) {
    return <Navigate to="/no-access" replace />;
  }
  return <Outlet />;
}

export function PermissionGuard({
  roles,
  children,
}: PropsWithChildren<{ roles: Role[] }>) {
  const auth = useAuth();
  if (!auth.user?.roles.some((role) => roles.includes(role))) {
    return <Navigate to="/no-access" replace />;
  }
  return children;
}

export function PublicOnly(): React.ReactNode {
  const auth = useAuth();
  if (auth.phase === "restoring") {
    return (
      <main className="session-gate" aria-busy="true">
        <span className="session-gate__brand">MoMo-FDVS</span>
        <Skeleton lines={2} label="Checking staff session" />
      </main>
    );
  }
  if (auth.phase === "authenticated") {
    const isStaff = auth.user?.roles.some((role) => staffRoles.has(role));
    return <Navigate to={isStaff ? "/dashboard" : "/no-access"} replace />;
  }
  return <Outlet />;
}
