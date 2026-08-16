import { File, Paths } from "expo-file-system";
import { isAvailableAsync, shareAsync } from "expo-sharing";
import { z } from "zod";

import type { JsonRequest } from "@/lib/api";
import {
  notificationListSchema,
  notificationSchema,
  ownerCaseSchema,
  readAllSchema,
  reportArtifactSchema,
  type AppNotification,
  type NotificationList,
  type OwnerCase,
  type ReportArtifact,
  unreadCountSchema,
} from "@/types/engagement";

export type AuthorizedResponse = (
  path: string,
  init?: RequestInit,
) => Promise<Response>;

const envelopeSchema = z
  .object({
    data: z.unknown(),
    meta: z.record(z.string(), z.unknown()),
  })
  .strict();

export class EngagementContractError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "EngagementContractError";
  }
}

function parseEnvelope<T extends z.ZodType>(
  schema: T,
  payload: unknown,
  message: string,
): z.infer<T> {
  const envelope = envelopeSchema.safeParse(payload);
  if (!envelope.success) throw new EngagementContractError(message);
  const parsed = schema.safeParse(envelope.data.data);
  if (!parsed.success) throw new EngagementContractError(message);
  return parsed.data;
}

export function createEngagementKey(prefix: "report" | "case"): string {
  const random =
    globalThis.crypto?.randomUUID?.() ??
    `${Date.now()}-${Math.random().toString(36).slice(2)}`;
  return `${prefix}-${random}`;
}

export async function listNotifications(
  request: JsonRequest,
  unread = false,
): Promise<NotificationList> {
  const response = await request<unknown>(
    `/api/v1/notifications?unread=${unread}&page=1&page_size=50`,
  );
  return parseEnvelope(
    notificationListSchema,
    response,
    "Notification response is incompatible.",
  );
}

export async function getUnreadCount(request: JsonRequest): Promise<number> {
  const response = await request<unknown>("/api/v1/notifications/unread-count");
  return parseEnvelope(
    unreadCountSchema,
    response,
    "Unread count response is incompatible.",
  ).unread_count;
}

export async function markNotificationRead(
  request: JsonRequest,
  notificationId: string,
): Promise<AppNotification> {
  const response = await request<unknown>(
    `/api/v1/notifications/${encodeURIComponent(notificationId)}/read`,
    { method: "POST" },
  );
  return parseEnvelope(
    notificationSchema,
    response,
    "Notification read response is incompatible.",
  );
}

export async function markAllNotificationsRead(
  request: JsonRequest,
): Promise<number> {
  const response = await request<unknown>("/api/v1/notifications/read-all", {
    method: "POST",
  });
  return parseEnvelope(
    readAllSchema,
    response,
    "Notification read-all response is incompatible.",
  ).marked_read;
}

export async function createAnalysisReport(
  request: JsonRequest,
  transactionId: string,
  idempotencyKey: string,
): Promise<ReportArtifact> {
  const response = await request<unknown>(
    `/api/v1/transactions/${encodeURIComponent(transactionId)}/reports`,
    {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey },
      body: JSON.stringify({ format: "HTML" }),
    },
  );
  return parseEnvelope(
    reportArtifactSchema,
    response,
    "Report response is incompatible.",
  );
}

export async function saveAndShareReport(
  response: AuthorizedResponse,
  report: ReportArtifact,
  sharing: {
    isAvailable: () => Promise<boolean>;
    share: (
      uri: string,
      options: { mimeType: string; dialogTitle: string },
    ) => Promise<void>;
  } = { isAvailable: isAvailableAsync, share: shareAsync },
): Promise<"downloaded" | "shared"> {
  if (!report.download_url || report.status !== "READY") {
    throw new EngagementContractError("The report is not ready to download.");
  }
  const download = await response(report.download_url);
  const content = new Uint8Array(await download.arrayBuffer());
  if (process.env.EXPO_OS === "web") {
    const objectUrl = URL.createObjectURL(
      new Blob([content], { type: "text/html;charset=utf-8" }),
    );
    const link = document.createElement("a");
    link.href = objectUrl;
    link.download = `momo-analysis-${report.id}.html`;
    link.click();
    URL.revokeObjectURL(objectUrl);
    return "downloaded";
  }
  const file = new File(Paths.cache, `momo-analysis-${report.id}.html`);
  file.create({ overwrite: true });
  file.write(content);
  if (await sharing.isAvailable()) {
    await sharing.share(file.uri, {
      mimeType: "text/html",
      dialogTitle: "Save or share analysis report",
    });
    return "shared";
  }
  throw new EngagementContractError("Sharing is unavailable on this device.");
}

export async function createFraudReport(
  request: JsonRequest,
  transactionId: string,
  idempotencyKey: string,
  input: { category: string; description?: string },
): Promise<OwnerCase> {
  const response = await request<unknown>(
    `/api/v1/transactions/${encodeURIComponent(transactionId)}/fraud-reports`,
    {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey },
      body: JSON.stringify(input),
    },
  );
  return parseEnvelope(
    ownerCaseSchema,
    response,
    "Fraud report response is incompatible.",
  );
}

export async function getFraudReport(
  request: JsonRequest,
  caseId: string,
): Promise<OwnerCase> {
  const response = await request<unknown>(
    `/api/v1/fraud-reports/${encodeURIComponent(caseId)}`,
  );
  return parseEnvelope(
    ownerCaseSchema,
    response,
    "Case response is incompatible.",
  );
}
