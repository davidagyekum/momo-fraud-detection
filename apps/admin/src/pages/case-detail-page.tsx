import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useAuth } from "../auth/use-auth";
import {
  Alert,
  Skeleton,
  StatePanel,
  StatusBadge,
} from "../components/feedback";
import { Dialog } from "../components/overlays";
import { Button, FormField, Surface } from "../components/primitives";
import {
  addCaseNote,
  assignCase,
  createCaseReport,
  decideCase,
  getCase,
  startReview,
} from "../lib/operations";

const readable = (value: string) => value.toLowerCase().replaceAll("_", " ");

export function CaseDetailPage(): React.ReactNode {
  const { caseId = "" } = useParams();
  const { download, request, user } = useAuth();
  const client = useQueryClient();
  const [investigatorId, setInvestigatorId] = useState(
    user?.roles.includes("INVESTIGATOR") ? user.id : "",
  );
  const [note, setNote] = useState("");
  const [outcome, setOutcome] = useState("CONFIRMED");
  const [reason, setReason] = useState("");
  const [decisionOpen, setDecisionOpen] = useState(false);
  const reportKey = useRef(`case-report-${crypto.randomUUID()}`);
  const query = useQuery({
    queryKey: ["case", caseId],
    queryFn: () => getCase(request, caseId),
    enabled: Boolean(caseId),
    staleTime: 0,
  });
  const refresh = () =>
    client.invalidateQueries({ queryKey: ["case", caseId] });
  const mutation = useMutation({
    mutationFn: async (action: "assign" | "start" | "note" | "decision") => {
      if (!query.data) throw new Error("The case must be loaded first.");
      if (action === "assign")
        return assignCase(request, caseId, investigatorId, query.data.version);
      if (action === "start")
        return startReview(request, caseId, query.data.version);
      if (action === "note")
        return addCaseNote(request, caseId, query.data.version, note.trim());
      return decideCase(
        request,
        caseId,
        query.data.version,
        outcome,
        reason.trim(),
      );
    },
    onSuccess: () => {
      setNote("");
      setReason("");
      setDecisionOpen(false);
      void refresh();
    },
  });
  const report = useMutation({
    mutationFn: async () => {
      const artifact = await createCaseReport(
        request,
        caseId,
        reportKey.current,
      );
      await download(artifact.download_url, `momo-case-${caseId}.html`);
    },
  });
  if (query.isPending)
    return <Skeleton lines={10} label="Loading investigation case" />;
  if (query.isError)
    return (
      <StatePanel
        kind="error"
        title="Case unavailable"
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
          <h1>Case workspace</h1>
          <p>
            {readable(item.category)} · version {item.version}
          </p>
        </div>
        <Link to="/cases">Back to queue</Link>
      </header>
      {mutation.isError ? (
        <Alert tone="danger" title="Case update failed" live>
          {mutation.error.message}
        </Alert>
      ) : null}
      {report.isError ? (
        <Alert tone="danger" title="Case report unavailable" live>
          {report.error.message}
        </Alert>
      ) : null}
      <section className="summary-band" aria-label="Case status summary">
        <div>
          <span>Status</span>
          <strong>{readable(item.status)}</strong>
        </div>
        <div>
          <span>Source</span>
          <strong>{readable(item.source)}</strong>
        </div>
        <div>
          <span>Fraud risk</span>
          <strong>
            {readable(item.automated_evidence?.risk_band ?? "unavailable")}
          </strong>
        </div>
        <div>
          <span>Automated evidence</span>
          <strong>
            {item.automated_evidence?.immutable ? "immutable" : "unavailable"}
          </strong>
        </div>
      </section>
      <Alert tone="neutral">
        Human decisions append to this case and never alter the automated
        result.
      </Alert>
      <Button
        variant="secondary"
        onClick={() => report.mutate()}
        loading={report.isPending}
      >
        Generate and download case report
      </Button>
      {item.status === "OPEN" ? (
        <Surface>
          <h2>Assignment</h2>
          <FormField
            label="Investigator ID"
            value={investigatorId}
            onChange={(event) => setInvestigatorId(event.target.value)}
            hint="Use your own ID when self-assigning."
          />
          <Button
            onClick={() => mutation.mutate("assign")}
            loading={mutation.isPending}
            disabled={!investigatorId}
          >
            Assign case
          </Button>
        </Surface>
      ) : null}
      {item.status === "ASSIGNED" ? (
        <Button
          onClick={() => mutation.mutate("start")}
          loading={mutation.isPending}
        >
          Start review
        </Button>
      ) : null}
      {item.status === "IN_REVIEW" ? (
        <div className="workspace-grid">
          <Surface>
            <h2>Add investigation note</h2>
            <div className="form-field">
              <label htmlFor="case-note">Note</label>
              <textarea
                id="case-note"
                value={note}
                onChange={(event) => setNote(event.target.value)}
                maxLength={4000}
                rows={5}
              />
            </div>
            <Button
              onClick={() => mutation.mutate("note")}
              disabled={!note.trim()}
              loading={mutation.isPending}
            >
              Add note
            </Button>
          </Surface>
          <Surface>
            <h2>Record decision</h2>
            <div className="form-field">
              <label htmlFor="case-outcome">Outcome</label>
              <select
                id="case-outcome"
                value={outcome}
                onChange={(event) => setOutcome(event.target.value)}
              >
                <option value="CONFIRMED">Confirmed</option>
                <option value="DISMISSED">Dismissed</option>
                <option value="ESCALATED">Escalated</option>
              </select>
            </div>
            <div className="form-field">
              <label htmlFor="case-reason">Reason</label>
              <textarea
                id="case-reason"
                value={reason}
                onChange={(event) => setReason(event.target.value)}
                maxLength={4000}
                rows={5}
              />
            </div>
            <Button
              variant="danger"
              onClick={() => setDecisionOpen(true)}
              disabled={!reason.trim()}
            >
              Review decision
            </Button>
          </Surface>
        </div>
      ) : null}
      <Surface>
        <h2>Append-only timeline</h2>
        {item.timeline?.length ? (
          <ol className="timeline-list">
            {item.timeline.map((event) => (
              <li key={event.id}>
                <StatusBadge tone="neutral">
                  {readable(event.event_type)}
                </StatusBadge>
                <span>{new Date(event.created_at).toLocaleString()}</span>
                {event.reason ? <p>{event.reason}</p> : null}
              </li>
            ))}
          </ol>
        ) : (
          <p>No case events recorded.</p>
        )}
      </Surface>
      <Dialog
        open={decisionOpen}
        title="Confirm investigation decision"
        onClose={() => setDecisionOpen(false)}
        footer={
          <>
            <Button variant="secondary" onClick={() => setDecisionOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="danger"
              onClick={() => mutation.mutate("decision")}
              loading={mutation.isPending}
            >
              Record {readable(outcome)}
            </Button>
          </>
        }
      >
        <p>
          This decision is append-only. The automated evidence remains
          unchanged.
        </p>
        <p>
          <strong>Reason:</strong> {reason}
        </p>
      </Dialog>
    </div>
  );
}
