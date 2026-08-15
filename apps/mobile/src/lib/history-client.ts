import { z } from "zod";

import type { JsonRequest } from "@/lib/api";
import {
  historyFiltersSchema,
  transactionDetailSchema,
  transactionHistorySchema,
  type HistoryFilters,
  type TransactionDetail,
  type TransactionHistory,
} from "@/types/history";

const envelopeSchema = z
  .object({
    data: z.unknown(),
    meta: z.record(z.string(), z.unknown()),
  })
  .strict();

export class HistoryContractError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "HistoryContractError";
  }
}

function parseHistory<T extends z.ZodType>(
  schema: T,
  payload: unknown,
  message: string,
): z.infer<T> {
  const envelope = envelopeSchema.safeParse(payload);
  if (!envelope.success) throw new HistoryContractError(message);
  const parsed = schema.safeParse(envelope.data.data);
  if (!parsed.success) throw new HistoryContractError(message);
  return parsed.data;
}

export async function listTransactions(
  request: JsonRequest,
  filters: HistoryFilters = {},
): Promise<TransactionHistory> {
  const parsed = historyFiltersSchema.safeParse(filters);
  if (!parsed.success)
    throw new HistoryContractError("History filters are invalid.");
  const query = new URLSearchParams();
  const values = parsed.data;
  if (values.page !== undefined) query.set("page", String(values.page));
  if (values.page_size !== undefined)
    query.set("page_size", String(values.page_size));
  if (values.provider !== undefined) query.set("provider", values.provider);
  if (values.status !== undefined) query.set("status", values.status);
  if (values.verification !== undefined)
    query.set("verification", values.verification);
  if (values.band !== undefined) query.set("band", values.band);
  const suffix = query.size > 0 ? `?${query.toString()}` : "";
  const response = await request<unknown>(`/api/v1/transactions${suffix}`);
  return parseHistory(
    transactionHistorySchema,
    response,
    "History response is incompatible.",
  );
}

export async function getTransaction(
  request: JsonRequest,
  transactionId: string,
): Promise<TransactionDetail> {
  const response = await request<unknown>(
    `/api/v1/transactions/${encodeURIComponent(transactionId)}`,
  );
  return parseHistory(
    transactionDetailSchema,
    response,
    "Transaction response is incompatible.",
  );
}
