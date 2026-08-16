import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useAuth } from "../auth/use-auth";
import {
  DataTable,
  Pagination,
  type DataColumn,
} from "../components/data-table";
import {
  Alert,
  Skeleton,
  StatePanel,
  StatusBadge,
} from "../components/feedback";
import {
  getAuditLogs,
  getModels,
  getRuleSets,
  getSystemStatus,
} from "../lib/operations";

type AuditRow = Awaited<ReturnType<typeof getAuditLogs>>["items"][number];
type ModelRow = Awaited<ReturnType<typeof getModels>>["items"][number];
type RuleRow = Awaited<ReturnType<typeof getRuleSets>>["items"][number];

const auditColumns: DataColumn<AuditRow>[] = [
  {
    id: "time",
    header: "Time",
    cell: (row) => new Date(row.created_at).toLocaleString(),
  },
  { id: "action", header: "Action", cell: (row) => row.action },
  { id: "target", header: "Target", cell: (row) => row.target_type },
  {
    id: "roles",
    header: "Actor roles",
    cell: (row) => row.actor_roles.join(", ") || "System",
  },
  {
    id: "outcome",
    header: "Outcome",
    cell: (row) => (
      <StatusBadge
        tone={
          row.outcome === "SUCCESS"
            ? "success"
            : row.outcome === "DENIED"
              ? "warning"
              : "danger"
        }
      >
        {row.outcome.toLowerCase()}
      </StatusBadge>
    ),
  },
];

export function AuditLogsPage(): React.ReactNode {
  const { request } = useAuth();
  const [page, setPage] = useState(1);
  const query = useQuery({
    queryKey: ["audit-logs", page],
    queryFn: () => getAuditLogs(request, page),
  });
  if (query.isPending)
    return <Skeleton lines={10} label="Loading audit logs" />;
  if (query.isError)
    return (
      <StatePanel
        kind="error"
        title="Audit logs unavailable"
        description={query.error.message}
        actionLabel="Retry"
        onAction={() => void query.refetch()}
      />
    );
  return (
    <div className="page-stack">
      <header className="page-heading">
        <div>
          <h1>Audit logs</h1>
          <p>Append-only safe privileged and evidential events.</p>
        </div>
      </header>
      <Alert tone="neutral">
        Sensitive metadata and request fingerprints are not exposed in this
        view.
      </Alert>
      <DataTable
        caption="Audit events"
        columns={auditColumns}
        rows={query.data.items}
        rowKey={(row) => row.id}
        emptyTitle="No audit events"
        emptyDescription="No authorised events are recorded."
      />
      <Pagination
        page={page}
        pageCount={query.data.total_pages}
        onPageChange={setPage}
      />
    </div>
  );
}

export function SystemStatusPage(): React.ReactNode {
  const { request } = useAuth();
  const query = useQuery({
    queryKey: ["system-status"],
    queryFn: () => getSystemStatus(request),
    refetchInterval: 30_000,
  });
  if (query.isPending)
    return <Skeleton lines={8} label="Loading dependency status" />;
  if (query.isError)
    return (
      <StatePanel
        kind="error"
        title="System status unavailable"
        description={query.error.message}
        actionLabel="Retry"
        onAction={() => void query.refetch()}
      />
    );
  return (
    <div className="page-stack">
      <header className="page-heading">
        <div>
          <h1>System status</h1>
          <p>Safe readiness without host paths or credentials.</p>
        </div>
      </header>
      <section className="summary-band" aria-label="Readiness summary">
        <div>
          <span>Core API</span>
          <strong>{query.data.ready ? "ready" : "unavailable"}</strong>
        </div>
        <div>
          <span>Analysis</span>
          <strong>
            {query.data.analysis_available ? "available" : "degraded"}
          </strong>
        </div>
        <div>
          <span>Full model analysis</span>
          <strong>
            {query.data.full_analysis_available ? "available" : "degraded"}
          </strong>
        </div>
      </section>
      <div className="workspace-grid">
        {Object.entries(query.data.components).map(([name, component]) => (
          <section className="surface" key={name}>
            <h2>{name.replaceAll("_", " ")}</h2>
            <StatusBadge
              tone={
                component.status === "ready"
                  ? "success"
                  : component.status === "unavailable"
                    ? "danger"
                    : "warning"
              }
            >
              {component.status}
            </StatusBadge>
            {component.reason ? (
              <p>{component.reason.replaceAll("_", " ")}</p>
            ) : null}
            {component.version ? <p>Version {component.version}</p> : null}
          </section>
        ))}
      </div>
    </div>
  );
}

const modelColumns: DataColumn<ModelRow>[] = [
  { id: "type", header: "Type", cell: (row) => row.model_type.toLowerCase() },
  { id: "name", header: "Model", cell: (row) => row.name },
  { id: "version", header: "Version", cell: (row) => row.version },
  {
    id: "preprocessing",
    header: "Preprocessing",
    cell: (row) => row.preprocessing_version,
  },
  {
    id: "status",
    header: "Status",
    cell: (row) => (
      <StatusBadge
        tone={
          row.status === "ACTIVE"
            ? "success"
            : row.status === "FAILED"
              ? "danger"
              : "warning"
        }
      >
        {row.status.toLowerCase()}
      </StatusBadge>
    ),
  },
];

export function ModelsPage(): React.ReactNode {
  const { request } = useAuth();
  const query = useQuery({
    queryKey: ["models"],
    queryFn: () => getModels(request),
  });
  if (query.isPending)
    return <Skeleton lines={8} label="Loading model registry" />;
  if (query.isError)
    return (
      <StatePanel
        kind="error"
        title="Models unavailable"
        description={query.error.message}
        actionLabel="Retry"
        onAction={() => void query.refetch()}
      />
    );
  return (
    <div className="page-stack">
      <header className="page-heading">
        <div>
          <h1>Model registry</h1>
          <p>Read-only artifact readiness and version identities.</p>
        </div>
      </header>
      <Alert tone="warning">
        Unavailable or rejected classifiers are never represented as ready.
      </Alert>
      <DataTable
        caption="Registered models"
        columns={modelColumns}
        rows={query.data.items}
        rowKey={(row) => row.id}
        emptyTitle="No models registered"
        emptyDescription="No trusted model artifact is registered."
      />
    </div>
  );
}

const ruleColumns: DataColumn<RuleRow>[] = [
  { id: "version", header: "Version", cell: (row) => row.version },
  { id: "description", header: "Description", cell: (row) => row.description },
  {
    id: "rules",
    header: "Rules",
    cell: (row) => row.rule_count,
    numeric: true,
  },
  {
    id: "row-version",
    header: "Row version",
    cell: (row) => row.row_version,
    numeric: true,
  },
  {
    id: "status",
    header: "Status",
    cell: (row) => (
      <StatusBadge tone={row.status === "ACTIVE" ? "success" : "neutral"}>
        {row.status.toLowerCase()}
      </StatusBadge>
    ),
  },
];

export function RulesPage(): React.ReactNode {
  const { request } = useAuth();
  const query = useQuery({
    queryKey: ["rule-sets"],
    queryFn: () => getRuleSets(request),
  });
  if (query.isPending) return <Skeleton lines={8} label="Loading rule sets" />;
  if (query.isError)
    return (
      <StatePanel
        kind="error"
        title="Rule sets unavailable"
        description={query.error.message}
        actionLabel="Retry"
        onAction={() => void query.refetch()}
      />
    );
  return (
    <div className="page-stack">
      <header className="page-heading">
        <div>
          <h1>Fraud rules</h1>
          <p>Read-only versioned rule-set identities.</p>
        </div>
      </header>
      <DataTable
        caption="Fraud rule sets"
        columns={ruleColumns}
        rows={query.data.items}
        rowKey={(row) => row.id}
        emptyTitle="No rule sets"
        emptyDescription="No rule set is registered."
      />
    </div>
  );
}
