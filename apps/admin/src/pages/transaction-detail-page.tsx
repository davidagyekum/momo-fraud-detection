import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { useAuth } from "../auth/use-auth";
import {
  Alert,
  Skeleton,
  StatePanel,
  StatusBadge,
} from "../components/feedback";
import { Surface } from "../components/primitives";
import { getTransaction } from "../lib/operations";

const readable = (value: string) => value.toLowerCase().replaceAll("_", " ");

export function TransactionDetailPage(): React.ReactNode {
  const { transactionId = "" } = useParams();
  const { request } = useAuth();
  const query = useQuery({
    queryKey: ["admin-transaction", transactionId],
    queryFn: () => getTransaction(request, transactionId),
    enabled: Boolean(transactionId),
  });
  if (query.isPending)
    return <Skeleton lines={8} label="Loading transaction evidence" />;
  if (query.isError)
    return (
      <StatePanel
        kind="error"
        title="Transaction unavailable"
        description={query.error.message}
        actionLabel="Retry"
        onAction={() => void query.refetch()}
      />
    );
  const item = query.data;
  return (
    <div className="page-stack">
      <header className="page-heading">
        <div>
          <h1>Transaction evidence</h1>
          <p>
            {item.display_reference_masked ?? "Masked reference unavailable"}
          </p>
        </div>
        <Link to="/transactions">Back to transactions</Link>
      </header>
      <Alert tone="neutral">
        Protected receipt evidence remains behind audited private endpoints.
      </Alert>
      <section className="summary-band" aria-label="Transaction result summary">
        <div>
          <span>Transaction</span>
          <strong>{readable(item.status)}</strong>
        </div>
        <div>
          <span>Fraud risk</span>
          <strong>
            {readable(item.analysis?.risk_band ?? "not analysed")}
          </strong>
        </div>
        <div>
          <span>Verification</span>
          <strong>
            {readable(item.analysis?.verification_status ?? "unverified")}
          </strong>
        </div>
        <div>
          <span>Case</span>
          <strong>{readable(item.case?.status ?? "none")}</strong>
        </div>
      </section>
      <Surface>
        <h2>Evidence controls</h2>
        <StatusBadge
          tone={item.automated_evidence_immutable ? "success" : "warning"}
        >
          Automated evidence immutable
        </StatusBadge>
        <p>{item.ocr_confirmation_count ?? 0} OCR confirmation snapshot(s)</p>
        <p>Receipt available: {item.receipt_available ? "yes" : "no"}</p>
      </Surface>
    </div>
  );
}
