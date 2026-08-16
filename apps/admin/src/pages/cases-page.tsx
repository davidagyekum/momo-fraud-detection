import { useQuery } from "@tanstack/react-query";
import { ExternalLink } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../auth/use-auth";
import {
  DataTable,
  Pagination,
  type DataColumn,
} from "../components/data-table";
import { Skeleton, StatePanel, StatusBadge } from "../components/feedback";
import { getCases, type CaseRow } from "../lib/operations";

const readable = (value: string) => value.toLowerCase().replaceAll("_", " ");
const columns: DataColumn<CaseRow>[] = [
  {
    id: "opened",
    header: "Opened",
    cell: (row) => new Date(row.opened_at).toLocaleString(),
  },
  { id: "category", header: "Category", cell: (row) => readable(row.category) },
  { id: "source", header: "Source", cell: (row) => readable(row.source) },
  {
    id: "status",
    header: "Status",
    cell: (row) => (
      <StatusBadge tone={row.status === "DECIDED" ? "success" : "warning"}>
        {readable(row.status)}
      </StatusBadge>
    ),
  },
  {
    id: "version",
    header: "Version",
    cell: (row) => row.version,
    numeric: true,
  },
  {
    id: "open",
    header: "",
    cell: (row) => (
      <Link to={`/cases/${row.id}`} aria-label="Open case">
        <ExternalLink size={18} />
      </Link>
    ),
  },
];

export function CasesPage(): React.ReactNode {
  const { request } = useAuth();
  const [page, setPage] = useState(1);
  const query = useQuery({
    queryKey: ["cases", page],
    queryFn: () => getCases(request, page),
  });
  if (query.isPending)
    return <Skeleton lines={9} label="Loading investigation queue" />;
  if (query.isError)
    return (
      <StatePanel
        kind="error"
        title="Cases unavailable"
        description={query.error.message}
        actionLabel="Retry"
        onAction={() => void query.refetch()}
      />
    );
  return (
    <div className="page-stack">
      <header className="page-heading">
        <div>
          <h1>Investigation queue</h1>
          <p>Append-only casework with optimistic version checks.</p>
        </div>
      </header>
      <DataTable
        caption="Fraud investigation cases"
        columns={columns}
        rows={query.data.items}
        rowKey={(row) => row.id}
        emptyTitle="No active cases"
        emptyDescription="Reported or configured high-risk cases will appear here."
      />
      <Pagination
        page={page}
        pageCount={query.data.total_pages}
        onPageChange={setPage}
      />
    </div>
  );
}
