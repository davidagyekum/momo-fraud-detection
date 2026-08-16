import { useQuery } from "@tanstack/react-query";
import {
  BriefcaseBusiness,
  Gauge,
  RefreshCw,
  Settings2,
  ShieldCheck,
} from "lucide-react";
import { useAuth } from "../auth/use-auth";
import { DataTable, type DataColumn } from "../components/data-table";
import { Skeleton, StatePanel } from "../components/feedback";
import { Button } from "../components/primitives";
import { getDashboard, type DashboardData } from "../lib/operations";

type Activity = DashboardData["recent_activity"][number];

const activityColumns: DataColumn<Activity>[] = [
  {
    id: "time",
    header: "Time",
    cell: (row) => new Date(row.created_at).toLocaleString(),
  },
  {
    id: "action",
    header: "Action",
    cell: (row) => row.action.replaceAll("_", " "),
  },
  {
    id: "target",
    header: "Target",
    cell: (row) => row.target_type.replaceAll("_", " "),
  },
  { id: "outcome", header: "Outcome", cell: (row) => row.outcome },
];

const total = (counts: Record<string, number>) =>
  Object.values(counts).reduce((sum, value) => sum + value, 0);

export function DashboardPage(): React.ReactNode {
  const { request } = useAuth();
  const dashboard = useQuery({
    queryKey: ["operations-dashboard"],
    queryFn: () => getDashboard(request),
  });
  if (dashboard.isPending)
    return <Skeleton lines={8} label="Loading operational dashboard" />;
  if (dashboard.isError) {
    return (
      <StatePanel
        kind="error"
        title="Dashboard unavailable"
        description={dashboard.error.message}
        actionLabel="Retry"
        onAction={() => void dashboard.refetch()}
      />
    );
  }
  const data = dashboard.data;
  const summaries = [
    { label: "Fraud risk", value: total(data.risk_counts), icon: ShieldCheck },
    {
      label: "Verification status",
      value: total(data.verification_counts),
      icon: Gauge,
    },
    {
      label: "Case status",
      value: total(data.case_status_counts),
      icon: BriefcaseBusiness,
    },
    {
      label: "Processing state",
      value: total(data.analysis_status_counts),
      icon: Settings2,
    },
  ];
  return (
    <div className="page-stack">
      <header className="page-heading">
        <div>
          <h1>Operations overview</h1>
          <p>Fraud risk, verification and human case state remain separate.</p>
        </div>
        <Button
          variant="secondary"
          icon={<RefreshCw size={18} />}
          onClick={() => void dashboard.refetch()}
          loading={dashboard.isFetching}
        >
          Refresh
        </Button>
      </header>
      <section
        className="summary-band"
        aria-label="Operational status categories"
      >
        {summaries.map(({ label, value, icon: Icon }) => (
          <div key={label}>
            <Icon size={26} strokeWidth={1.7} aria-hidden="true" />
            <span>{label}</span>
            <strong>{value}</strong>
          </div>
        ))}
      </section>
      <section
        className="activity-section"
        aria-labelledby="recent-activity-title"
      >
        <h2 id="recent-activity-title">Recent safe activity</h2>
        <DataTable
          caption="Recent authorised staff activity"
          columns={activityColumns}
          rows={data.recent_activity}
          rowKey={(row) => row.id}
          emptyTitle="No activity recorded"
          emptyDescription="Audited activity will appear after staff actions occur."
        />
      </section>
    </div>
  );
}
