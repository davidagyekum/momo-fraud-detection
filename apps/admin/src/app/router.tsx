import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "./app-shell";
import { PermissionGuard, PublicOnly, SessionGate } from "./guards";
import { portalRoutes, profileRoute } from "./routes";
import { DashboardPage } from "../pages/dashboard-page";
import { CaseDetailPage } from "../pages/case-detail-page";
import { CasesPage } from "../pages/cases-page";
import { FeatureShellPage } from "../pages/feature-shell-page";
import { ForgotPasswordPage } from "../pages/forgot-password-page";
import { LoginPage } from "../pages/login-page";
import { ProfilePage } from "../pages/profile-page";
import {
  AuditLogsPage,
  ModelsPage,
  RulesPage,
  SystemStatusPage,
} from "../pages/operations-pages";
import { ReferenceImportsPage } from "../pages/reference-imports-page";
import { ReportsPage } from "../pages/reports-page";
import { TransactionDetailPage } from "../pages/transaction-detail-page";
import { TransactionsPage } from "../pages/transactions-page";
import { NoAccessPage, NotFoundPage } from "../pages/system-pages";

export function AppRouter(): React.ReactNode {
  return (
    <Routes>
      <Route element={<PublicOnly />}>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
      </Route>
      <Route path="/no-access" element={<NoAccessPage />} />
      <Route element={<SessionGate />}>
        <Route element={<AppShell />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          {portalRoutes.map((route) => (
            <Route
              key={route.path}
              path={route.path}
              element={
                <PermissionGuard roles={route.roles}>
                  {route.path === "/dashboard" ? (
                    <DashboardPage />
                  ) : route.path === "/transactions" ? (
                    <TransactionsPage />
                  ) : route.path === "/cases" ? (
                    <CasesPage />
                  ) : route.path === "/reference-imports" ? (
                    <ReferenceImportsPage />
                  ) : route.path === "/audit-logs" ? (
                    <AuditLogsPage />
                  ) : route.path === "/system-status" ? (
                    <SystemStatusPage />
                  ) : route.path === "/models" ? (
                    <ModelsPage />
                  ) : route.path === "/rules" ? (
                    <RulesPage />
                  ) : route.path === "/reports" ? (
                    <ReportsPage />
                  ) : (
                    <FeatureShellPage route={route} />
                  )}
                </PermissionGuard>
              }
            />
          ))}
          <Route
            path="/transactions/:transactionId"
            element={
              <PermissionGuard roles={["ADMIN", "INVESTIGATOR"]}>
                <TransactionDetailPage />
              </PermissionGuard>
            }
          />
          <Route
            path="/cases/:caseId"
            element={
              <PermissionGuard roles={["ADMIN", "INVESTIGATOR"]}>
                <CaseDetailPage />
              </PermissionGuard>
            }
          />
          <Route
            path={profileRoute.path}
            element={
              <PermissionGuard roles={profileRoute.roles}>
                <ProfilePage />
              </PermissionGuard>
            }
          />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Route>
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
