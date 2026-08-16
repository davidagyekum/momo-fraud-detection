import { useQuery } from "@tanstack/react-query";
import { Download } from "lucide-react";
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
import { Button } from "../components/primitives";
import { getReports } from "../lib/operations";

type ReportRow = Awaited<ReturnType<typeof getReports>>["items"][number];

export function ReportsPage(): React.ReactNode {
  const { download, request } = useAuth();
  const [page, setPage] = useState(1);
  const query = useQuery({
    queryKey: ["staff-reports", page],
    queryFn: () => getReports(request, page),
  });
  const columns: DataColumn<ReportRow>[] = [
    {
      id: "generated",
      header: "Generated",
      cell: (row) =>
        row.generated_at
          ? new Date(row.generated_at).toLocaleString()
          : "Pending",
    },
    { id: "case", header: "Case", cell: (row) => row.case_id },
    {
      id: "version",
      header: "Case version",
      cell: (row) => row.source_version,
      numeric: true,
    },
    {
      id: "status",
      header: "Status",
      cell: (row) => (
        <StatusBadge tone={row.status === "READY" ? "success" : "warning"}>
          {row.status.toLowerCase()}
        </StatusBadge>
      ),
    },
    {
      id: "download",
      header: "",
      cell: (row) =>
        row.download_url ? (
          <Button
            variant="ghost"
            icon={<Download size={17} />}
            onClick={() =>
              void download(
                row.download_url ?? "",
                `momo-case-${row.case_id}.html`,
              )
            }
          >
            Download
          </Button>
        ) : (
          "Unavailable"
        ),
    },
  ];
  if (query.isPending)
    return <Skeleton lines={8} label="Loading case reports" />;
  if (query.isError)
    return (
      <StatePanel
        kind="error"
        title="Reports unavailable"
        description={query.error.message}
        actionLabel="Retry"
        onAction={() => void query.refetch()}
      />
    );
  return (
    <div className="page-stack">
      <header className="page-heading">
        <div>
          <h1>Case reports</h1>
          <p>Version-bound, integrity-checked investigation records.</p>
        </div>
      </header>
      <Alert tone="neutral">
        Reports contain masked evidence and never include raw receipt images or
        storage paths.
      </Alert>
      <DataTable
        caption="Generated case reports"
        columns={columns}
        rows={query.data.items}
        rowKey={(row) => row.id}
        emptyTitle="No case reports"
        emptyDescription="Generate a report from a case workspace when evidence is ready."
      />
      <Pagination
        page={page}
        pageCount={query.data.total_pages}
        onPageChange={setPage}
      />
    </div>
  );
}
