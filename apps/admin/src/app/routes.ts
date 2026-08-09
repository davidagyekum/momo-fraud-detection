import {
  Activity,
  BookOpenCheck,
  BriefcaseBusiness,
  FileBarChart,
  FileClock,
  Gauge,
  Import,
  ListChecks,
  ScrollText,
  Settings2,
  ShieldCheck,
  Users,
  type LucideIcon,
} from "lucide-react";
import type { Role } from "../types/api";

export interface PortalRoute {
  path: string;
  label: string;
  shortLabel: string;
  icon: LucideIcon;
  roles: Role[];
  phase: string;
  description: string;
}

const staffRoles: Role[] = ["ADMIN", "INVESTIGATOR"];
const adminOnly: Role[] = ["ADMIN"];

export const portalRoutes: PortalRoute[] = [
  {
    path: "/dashboard",
    label: "Dashboard",
    shortLabel: "Dashboard",
    icon: Gauge,
    roles: staffRoles,
    phase: "P16",
    description: "Operational aggregates and component readiness.",
  },
  {
    path: "/transactions",
    label: "Transactions",
    shortLabel: "Transactions",
    icon: ListChecks,
    roles: staffRoles,
    phase: "P16",
    description: "Authorised transaction search with masked values.",
  },
  {
    path: "/cases",
    label: "Cases",
    shortLabel: "Cases",
    icon: BriefcaseBusiness,
    roles: staffRoles,
    phase: "P15",
    description: "Investigation queue, evidence review and reasoned decisions.",
  },
  {
    path: "/users",
    label: "Users",
    shortLabel: "Users",
    icon: Users,
    roles: adminOnly,
    phase: "P15",
    description: "Account status, roles, sessions and safeguards.",
  },
  {
    path: "/reference-imports",
    label: "Reference Imports",
    shortLabel: "Reference Imports",
    icon: Import,
    roles: adminOnly,
    phase: "P08/P15",
    description: "Validated stored-reference import and audit workflow.",
  },
  {
    path: "/templates",
    label: "Receipt Templates",
    shortLabel: "Templates",
    icon: BookOpenCheck,
    roles: adminOnly,
    phase: "P15",
    description: "Versioned receipt parser and template registry.",
  },
  {
    path: "/rules",
    label: "Fraud Rules",
    shortLabel: "Rules",
    icon: Settings2,
    roles: adminOnly,
    phase: "P15",
    description: "Versioned rules, thresholds, validation and rollback.",
  },
  {
    path: "/models",
    label: "Model Registry",
    shortLabel: "Models",
    icon: ShieldCheck,
    roles: adminOnly,
    phase: "P15",
    description: "Registered model versions and verified readiness.",
  },
  {
    path: "/reports",
    label: "Reports",
    shortLabel: "Reports",
    icon: FileBarChart,
    roles: staffRoles,
    phase: "P14/P15/P16",
    description: "Authorised analysis, case and operational reports.",
  },
  {
    path: "/audit-logs",
    label: "Audit Logs",
    shortLabel: "Audit Logs",
    icon: FileClock,
    roles: adminOnly,
    phase: "P16",
    description: "Append-only privileged and evidential action search.",
  },
  {
    path: "/system-status",
    label: "System Status",
    shortLabel: "System Status",
    icon: Activity,
    roles: adminOnly,
    phase: "P16",
    description: "Readiness for the API and analysis dependencies.",
  },
];

export const profileRoute: PortalRoute = {
  path: "/profile",
  label: "Profile / Security",
  shortLabel: "Profile",
  icon: ScrollText,
  roles: staffRoles,
  phase: "P05",
  description: "Current staff identity and session security.",
};

export function routeForPath(pathname: string): PortalRoute | undefined {
  return [...portalRoutes, profileRoute].find(
    (route) => route.path === pathname,
  );
}
