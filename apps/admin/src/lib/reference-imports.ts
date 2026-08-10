import type { ApiEnvelope } from "../types/api";

export type ImportStatus = "UPLOADED" | "VALIDATED" | "COMMITTED" | "FAILED";

export interface ReferenceImportBatch {
  id: string;
  source_label: string;
  original_filename: string;
  file_sha256: string;
  status: ImportStatus;
  total_rows: number;
  valid_rows: number;
  invalid_rows: number;
  validated_at: string | null;
  committed_at: string | null;
  created_at: string;
  invalid_rows_download: string | null;
}

export interface ReferenceImportList {
  imports: ReferenceImportBatch[];
  page: number;
  page_size: number;
  total: number;
}

export interface ValidationError {
  row: number;
  field: string;
  code: string;
  message: string;
}

export interface ReferenceValidation {
  batch: ReferenceImportBatch;
  errors: ValidationError[];
  preview_truncated: boolean;
}

export interface ReferenceCommit {
  batch: ReferenceImportBatch;
  committed_rows: number;
  replayed: boolean;
}

export type PortalRequester = <T>(
  path: string,
  init?: RequestInit,
) => Promise<ApiEnvelope<T>>;

export function listReferenceImports(
  request: PortalRequester,
): Promise<ApiEnvelope<ReferenceImportList>> {
  return request<ReferenceImportList>("/admin/reference-imports?page_size=100");
}

export function uploadReferenceImport(
  request: PortalRequester,
  sourceLabel: string,
  file: File,
  idempotencyKey: string,
): Promise<ApiEnvelope<ReferenceImportBatch>> {
  const body = new FormData();
  body.set("source_label", sourceLabel);
  body.set("file", file);
  return request<ReferenceImportBatch>("/admin/reference-imports", {
    method: "POST",
    headers: { "Idempotency-Key": idempotencyKey },
    body,
  });
}

export function validateReferenceImport(
  request: PortalRequester,
  batchId: string,
): Promise<ApiEnvelope<ReferenceValidation>> {
  return request<ReferenceValidation>(
    `/admin/reference-imports/${batchId}/validate`,
    { method: "POST", body: JSON.stringify({}) },
  );
}

export function commitReferenceImport(
  request: PortalRequester,
  batchId: string,
  idempotencyKey: string,
): Promise<ApiEnvelope<ReferenceCommit>> {
  return request<ReferenceCommit>(
    `/admin/reference-imports/${batchId}/commit`,
    {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey },
      body: JSON.stringify({}),
    },
  );
}

export function statusTone(
  status: ImportStatus,
): "info" | "warning" | "success" | "danger" {
  if (status === "COMMITTED") return "success";
  if (status === "VALIDATED") return "info";
  if (status === "FAILED") return "danger";
  return "warning";
}
