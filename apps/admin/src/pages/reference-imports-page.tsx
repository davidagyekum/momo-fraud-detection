import { Download, FileCheck2, Import, RefreshCw, Upload } from "lucide-react";
import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type SyntheticEvent,
} from "react";
import { useAuth } from "../auth/use-auth";
import {
  Alert,
  Skeleton,
  StatePanel,
  StatusBadge,
} from "../components/feedback";
import { Dialog } from "../components/overlays";
import { Button, FormField, Surface } from "../components/primitives";
import { ApiError } from "../lib/api";
import {
  commitReferenceImport,
  listReferenceImports,
  statusTone,
  uploadReferenceImport,
  validateReferenceImport,
  type ReferenceImportBatch,
  type ReferenceValidation,
} from "../lib/reference-imports";

function operationMessage(error: unknown): {
  message: string;
  requestId: string | null;
} {
  if (error instanceof ApiError) {
    return {
      message:
        error.status === 0
          ? "You appear to be offline. Reconnect and retry this operation."
          : error.message,
      requestId: error.requestId,
    };
  }
  return { message: "The operation could not be completed.", requestId: null };
}

export function ReferenceImportsPage(): React.ReactNode {
  const { request, download } = useAuth();
  const [imports, setImports] = useState<ReferenceImportBatch[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [sourceLabel, setSourceLabel] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<ReferenceValidation | null>(null);
  const [commitId, setCommitId] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<{
    message: string;
    requestId: string | null;
  } | null>(null);
  const operationKeys = useRef(new Map<string, string>());

  const refresh = useCallback(async (): Promise<void> => {
    setLoading(true);
    setError(null);
    try {
      const response = await listReferenceImports(request);
      setImports(response.data.imports);
    } catch (caught) {
      setError(operationMessage(caught));
    } finally {
      setLoading(false);
    }
  }, [request]);

  useEffect(() => {
    let active = true;
    void listReferenceImports(request)
      .then((response) => {
        if (active) setImports(response.data.imports);
      })
      .catch((caught: unknown) => {
        if (active) setError(operationMessage(caught));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [request]);

  const selectedCommit = imports.find((batch) => batch.id === commitId) ?? null;

  const stableKey = (operation: string): string => {
    const existing = operationKeys.current.get(operation);
    if (existing) return existing;
    const created = crypto.randomUUID();
    operationKeys.current.set(operation, created);
    return created;
  };

  const onUpload = async (
    event: SyntheticEvent<HTMLFormElement, SubmitEvent>,
  ): Promise<void> => {
    event.preventDefault();
    if (!file || sourceLabel.trim().length < 3) {
      setError({
        message:
          "Choose a CSV file and enter a source label of at least 3 characters.",
        requestId: null,
      });
      return;
    }
    const operation = `upload:${sourceLabel}:${file.name}:${String(file.size)}`;
    setBusy("upload");
    setError(null);
    try {
      const response = await uploadReferenceImport(
        request,
        sourceLabel.trim(),
        file,
        stableKey(operation),
      );
      operationKeys.current.delete(operation);
      setNotice(
        `Uploaded ${response.data.original_filename}. Validate it before committing.`,
      );
      setSourceLabel("");
      setFile(null);
      await refresh();
    } catch (caught) {
      setError(operationMessage(caught));
    } finally {
      setBusy(null);
    }
  };

  const onValidate = async (batchId: string): Promise<void> => {
    setBusy(`validate:${batchId}`);
    setError(null);
    try {
      const response = await validateReferenceImport(request, batchId);
      setPreview(response.data);
      setNotice(
        `Validation completed: ${String(response.data.batch.valid_rows)} valid, ${String(response.data.batch.invalid_rows)} invalid.`,
      );
      await refresh();
    } catch (caught) {
      setError(operationMessage(caught));
    } finally {
      setBusy(null);
    }
  };

  const onCommit = async (): Promise<void> => {
    if (!selectedCommit) return;
    const operation = `commit:${selectedCommit.id}`;
    setBusy(operation);
    setError(null);
    try {
      const response = await commitReferenceImport(
        request,
        selectedCommit.id,
        stableKey(operation),
      );
      operationKeys.current.delete(operation);
      setNotice(
        `Committed ${String(response.data.committed_rows)} stored reference records.`,
      );
      setCommitId(null);
      await refresh();
    } catch (caught) {
      setError(operationMessage(caught));
    } finally {
      setBusy(null);
    }
  };

  const downloadInvalidRows = async (
    batch: ReferenceImportBatch,
  ): Promise<void> => {
    if (!batch.invalid_rows_download) return;
    await download(
      batch.invalid_rows_download,
      `reference-import-${batch.id}-invalid-rows.csv`,
    );
  };

  return (
    <div className="page-stack reference-imports-page">
      <header className="page-heading">
        <div>
          <p className="eyebrow">Reference data control</p>
          <h1>Reference imports</h1>
          <p>
            Validate private provider exports before adding them to
            verification.
          </p>
        </div>
        <Button
          variant="secondary"
          icon={<RefreshCw size={18} />}
          onClick={() => void refresh()}
          loading={loading}
        >
          Refresh
        </Button>
      </header>

      <Alert tone="warning" title="Stored-reference verification">
        Verification uses reference data imported here. It is not a live
        mobile-network operator connection, and it is displayed separately from
        fraud risk.
      </Alert>
      {notice ? (
        <Alert tone="success" live>
          {notice}
        </Alert>
      ) : null}
      {error ? (
        <Alert tone="danger" title="Operation failed" live>
          {error.message}
          {error.requestId ? (
            <small> Request ID: {error.requestId}</small>
          ) : null}
        </Alert>
      ) : null}

      <Surface className="reference-upload-card">
        <div className="section-heading">
          <div>
            <span className="section-icon" aria-hidden="true">
              <Import size={22} />
            </span>
            <div>
              <h2>Upload a private CSV</h2>
              <p>
                The original file and invalid-row report remain in private
                storage.
              </p>
            </div>
          </div>
        </div>
        <form
          className="reference-upload-form"
          onSubmit={(event) => void onUpload(event)}
        >
          <FormField
            label="Source label"
            value={sourceLabel}
            onChange={(event) => setSourceLabel(event.target.value)}
            maxLength={200}
            hint="Use a recognisable, non-sensitive export label."
            required
          />
          <FormField
            label="Reference CSV"
            type="file"
            accept=".csv,text/csv"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            required
          />
          <Button
            type="submit"
            icon={<Upload size={18} />}
            loading={busy === "upload"}
          >
            Upload CSV
          </Button>
        </form>
      </Surface>

      {preview ? (
        <Surface className="validation-preview">
          <div className="section-heading">
            <div>
              <span className="section-icon" aria-hidden="true">
                <FileCheck2 size={22} />
              </span>
              <div>
                <h2>Latest validation preview</h2>
                <p>
                  {preview.batch.valid_rows} valid rows and{" "}
                  {preview.batch.invalid_rows} invalid rows in{" "}
                  {preview.batch.original_filename}.
                </p>
              </div>
            </div>
            {preview.batch.invalid_rows_download ? (
              <Button
                variant="secondary"
                icon={<Download size={18} />}
                onClick={() => void downloadInvalidRows(preview.batch)}
              >
                Download invalid rows
              </Button>
            ) : null}
          </div>
          {preview.errors.length ? (
            <div
              className="validation-errors"
              role="region"
              aria-label="Validation errors"
            >
              {preview.errors.map((item) => (
                <div key={`${String(item.row)}:${item.field}:${item.code}`}>
                  <strong>Row {item.row}</strong>
                  <span>{item.field}</span>
                  <code>{item.code}</code>
                  <p>{item.message}</p>
                </div>
              ))}
              {preview.preview_truncated ? (
                <p>
                  Only the first validation errors are shown. Download the
                  report for all.
                </p>
              ) : null}
            </div>
          ) : (
            <Alert tone="success">All rows passed validation.</Alert>
          )}
        </Surface>
      ) : null}

      <Surface className="reference-history">
        <div className="section-heading">
          <div>
            <h2>Import history</h2>
            <p>Upload, validation and commit are separate audited steps.</p>
          </div>
        </div>
        {loading ? (
          <Skeleton lines={5} label="Loading reference imports" />
        ) : error && imports.length === 0 ? (
          <StatePanel
            kind="error"
            title="Reference imports unavailable"
            description={error.message}
            actionLabel="Retry"
            onAction={() => void refresh()}
            requestId={error.requestId}
          />
        ) : imports.length === 0 ? (
          <StatePanel
            title="No reference imports"
            description="Upload a controlled CSV export to begin the validation workflow."
          />
        ) : (
          <div className="reference-table-wrap">
            <table className="reference-table">
              <caption>Private reference import history</caption>
              <thead>
                <tr>
                  <th>Source</th>
                  <th>Status</th>
                  <th>Rows</th>
                  <th>Uploaded</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {imports.map((batch) => (
                  <tr key={batch.id}>
                    <td>
                      <strong>{batch.source_label}</strong>
                      <small>{batch.original_filename}</small>
                    </td>
                    <td>
                      <StatusBadge tone={statusTone(batch.status)}>
                        {batch.status}
                      </StatusBadge>
                    </td>
                    <td>
                      {batch.total_rows || "—"}
                      {batch.status !== "UPLOADED" ? (
                        <small>
                          {batch.valid_rows} valid / {batch.invalid_rows}{" "}
                          invalid
                        </small>
                      ) : null}
                    </td>
                    <td>{new Date(batch.created_at).toLocaleString()}</td>
                    <td>
                      <div className="table-actions">
                        {batch.status !== "COMMITTED" ? (
                          <Button
                            variant="secondary"
                            onClick={() => void onValidate(batch.id)}
                            loading={busy === `validate:${batch.id}`}
                          >
                            Validate
                          </Button>
                        ) : null}
                        {batch.status === "VALIDATED" &&
                        batch.valid_rows > 0 ? (
                          <Button onClick={() => setCommitId(batch.id)}>
                            Review commit
                          </Button>
                        ) : null}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Surface>

      <Dialog
        open={Boolean(selectedCommit)}
        title="Commit stored reference records?"
        onClose={() => setCommitId(null)}
        footer={
          <>
            <Button variant="ghost" onClick={() => setCommitId(null)}>
              Cancel
            </Button>
            <Button
              variant="danger"
              onClick={() => void onCommit()}
              loading={busy === `commit:${selectedCommit?.id ?? ""}`}
            >
              Commit validated rows
            </Button>
          </>
        }
      >
        <Alert tone="warning" title="Audited evidence change">
          This adds {selectedCommit?.valid_rows ?? 0} immutable stored reference
          records. Invalid rows will not be committed. This cannot be presented
          as live provider verification.
        </Alert>
      </Dialog>
    </div>
  );
}
