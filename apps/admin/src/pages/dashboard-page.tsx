import {
  BriefcaseBusiness,
  Gauge,
  RefreshCw,
  Settings2,
  ShieldCheck,
} from "lucide-react";
import { useState } from "react";
import { Alert } from "../components/feedback";
import { DataTable, type DataColumn } from "../components/data-table";
import { Button } from "../components/primitives";

interface ActivityRow {
  id: string;
}

const emptyColumns: DataColumn<ActivityRow>[] = [
  { id: "submitted", header: "Submitted", cell: () => "—" },
  { id: "reference", header: "Masked reference", cell: () => "—" },
  { id: "risk", header: "Fraud risk", cell: () => "—" },
  { id: "verification", header: "Verification status", cell: () => "—" },
  { id: "case", header: "Case status", cell: () => "—" },
];

const summaries = [
  { label: "Fraud risk", icon: ShieldCheck },
  { label: "Verification status", icon: Gauge },
  { label: "Case status", icon: BriefcaseBusiness },
  { label: "Processing state", icon: Settings2 },
];

export function DashboardPage(): React.ReactNode {
  const [announcement, setAnnouncement] = useState("");
  return (
    <div className="page-stack">
      <header className="page-heading">
        <div>
          <h1>Operations overview</h1>
        </div>
        <Button
          variant="secondary"
          icon={<RefreshCw size={18} />}
          onClick={() =>
            setAnnouncement(
              "Shell state refreshed. Operational data remains unavailable in P05.",
            )
          }
        >
          Refresh
        </Button>
      </header>
      <p className="sr-only" aria-live="polite">
        {announcement}
      </p>
      <Alert>Operational data becomes available in later phases.</Alert>
      <section
        className="summary-band"
        aria-label="Operational status categories"
      >
        {summaries.map(({ label, icon: Icon }) => (
          <div key={label}>
            <Icon size={26} strokeWidth={1.7} aria-hidden="true" />
            <span>{label}</span>
            <strong aria-label={`${label} unavailable`}>—</strong>
          </div>
        ))}
      </section>
      <section
        className="activity-section"
        aria-labelledby="recent-activity-title"
      >
        <h2 id="recent-activity-title">Recent activity</h2>
        <DataTable
          caption="Recent authorised staff activity"
          columns={emptyColumns}
          rows={[]}
          rowKey={(row) => row.id}
          emptyTitle="No data available"
          emptyDescription="Operational data will be available in later phases."
        />
      </section>
    </div>
  );
}
