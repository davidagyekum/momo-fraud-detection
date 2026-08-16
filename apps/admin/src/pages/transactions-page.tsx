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
import { getTransactions, type TransactionRow } from "../lib/operations";

const readable = (value: string) => value.toLowerCase().replaceAll("_", " ");
const columns: DataColumn<TransactionRow>[] = [
  {
    id: "date",
    header: "Submitted",
    cell: (row) => new Date(row.created_at).toLocaleString(),
  },
  {
    id: "reference",
    header: "Masked reference",
    cell: (row) => row.display_reference_masked ?? "Not available",
  },
  {
    id: "risk",
    header: "Fraud risk",
    cell: (row) =>
      row.analysis ? (
        <StatusBadge tone="warning">
          {readable(row.analysis.risk_band)}
        </StatusBadge>
      ) : (
        "Not analysed"
      ),
  },
  {
    id: "verification",
    header: "Verification",
    cell: (row) => readable(row.analysis?.verification_status ?? "unverified"),
  },
  {
    id: "case",
    header: "Case",
    cell: (row) => readable(row.case?.status ?? "none"),
  },
  {
    id: "open",
    header: "",
    cell: (row) => (
      <Link to={`/transactions/${row.id}`} aria-label="Open transaction">
        <ExternalLink size={18} />
      </Link>
    ),
  },
];

export function TransactionsPage(): React.ReactNode {
  const { request } = useAuth();
  const [page, setPage] = useState(1);
  const query = useQuery({
    queryKey: ["admin-transactions", page],
    queryFn: () => getTransactions(request, page),
  });
  if (query.isPending)
    return <Skeleton lines={9} label="Loading transactions" />;
  if (query.isError)
    return (
      <StatePanel
        kind="error"
        title="Transactions unavailable"
        description={query.error.message}
        actionLabel="Retry"
        onAction={() => void query.refetch()}
      />
    );
  return (
    <div className="page-stack">
      <header className="page-heading">
        <div>
          <h1>Transactions</h1>
          <p>Masked evidence visible to authorised staff.</p>
        </div>
      </header>
      <DataTable
        caption="Authorised transactions"
        columns={columns}
        rows={query.data.items}
        rowKey={(row) => row.id}
        emptyTitle="No transactions"
        emptyDescription="No transactions match the current view."
      />
      <Pagination
        page={page}
        pageCount={query.data.total_pages}
        onPageChange={setPage}
      />
    </div>
  );
}
