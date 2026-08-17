import { z } from "zod";

import type { JsonRequest } from "@/lib/api";
import {
  analysisSchema,
  analysisStartSchema,
  type AnalysisResult,
  type AnalysisStart,
} from "@/types/analysis";

const envelopeSchema = z
  .object({
    data: z.unknown(),
    meta: z.record(z.string(), z.unknown()),
  })
  .strict();

const terminalStatuses = new Set([
  "COMPLETED",
  "PARTIAL",
  "FAILED",
  "CANCELLED",
]);

export class AnalysisContractError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "AnalysisContractError";
  }
}

export function createAnalysisIdempotencyKey(): string {
  const randomUuid = globalThis.crypto?.randomUUID?.();
  return randomUuid
    ? `analysis-${randomUuid}`
    : `analysis-${Date.now()}-${Math.random().toString(36).slice(2)}-${Math.random().toString(36).slice(2)}`;
}

function parseAnalysis<T extends z.ZodType>(
  schema: T,
  payload: unknown,
  message: string,
): z.infer<T> {
  const envelope = envelopeSchema.safeParse(payload);
  if (!envelope.success) throw new AnalysisContractError(message);
  const parsed = schema.safeParse(envelope.data.data);
  if (!parsed.success) throw new AnalysisContractError(message);
  return parsed.data;
}

function cancellationError(): Error {
  const error = new Error("Analysis polling was cancelled.");
  error.name = "AbortError";
  return error;
}

function defaultWait(milliseconds: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, milliseconds));
}

export async function startAnalysis(
  request: JsonRequest,
  transactionId: string,
  idempotencyKey: string,
  options?:
    | { mode: "screenshot_only"; ocrResultId: string }
    | { mode?: "combined"; ocrResultId?: never },
): Promise<AnalysisStart> {
  const body =
    options?.mode === "screenshot_only"
      ? JSON.stringify({
          mode: options.mode,
          ocr_result_id: options.ocrResultId,
        })
      : undefined;
  const response = await request<unknown>(
    `/api/v1/transactions/${encodeURIComponent(transactionId)}/analyses`,
    {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey },
      ...(body ? { body } : {}),
    },
  );
  return parseAnalysis(
    analysisStartSchema,
    response,
    "Analysis start response is incompatible.",
  );
}

export async function getAnalysis(
  request: JsonRequest,
  analysisRunId: string,
): Promise<AnalysisResult> {
  const response = await request<unknown>(
    `/api/v1/analyses/${encodeURIComponent(analysisRunId)}`,
  );
  return parseAnalysis(
    analysisSchema,
    response,
    "Analysis response is incompatible.",
  );
}

export async function pollAnalysis(
  request: JsonRequest,
  analysisRunId: string,
  options: {
    signal?: AbortSignal;
    maxAttempts?: number;
    wait?: (milliseconds: number) => Promise<void>;
  } = {},
): Promise<AnalysisResult> {
  const maxAttempts = options.maxAttempts ?? 12;
  if (!Number.isInteger(maxAttempts) || maxAttempts < 1 || maxAttempts > 100) {
    throw new AnalysisContractError("Analysis polling options are invalid.");
  }
  const wait = options.wait ?? defaultWait;
  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    if (options.signal?.aborted) throw cancellationError();
    const result = await getAnalysis(request, analysisRunId);
    if (terminalStatuses.has(result.status)) return result;
    if (attempt + 1 < maxAttempts) {
      await wait(Math.min(500 * 2 ** attempt, 5000));
      if (options.signal?.aborted) throw cancellationError();
    }
  }
  throw new AnalysisContractError("Analysis polling timed out.");
}
