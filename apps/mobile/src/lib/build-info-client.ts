import { z } from "zod";

import type { JsonRequest } from "@/lib/api";

const buildInfoSchema = z
  .object({
    application: z.string().min(1),
    version: z.string().min(1),
    build_commit: z.string().min(1),
    api_contract_version: z.string().min(1),
    ocr_pipeline_version: z.string().min(1),
    fraud_ruleset_version: z.string().min(1),
    risk_policy_version: z.string().min(1),
  })
  .strict();

const buildInfoEnvelopeSchema = z
  .object({
    data: buildInfoSchema,
    meta: z.record(z.string(), z.unknown()),
  })
  .strict();

export type BuildInfo = z.infer<typeof buildInfoSchema>;

export async function fetchBuildInfo(request: JsonRequest): Promise<BuildInfo> {
  const response = await request<unknown>("/api/v1/version");
  const parsed = buildInfoEnvelopeSchema.safeParse(response);
  if (!parsed.success) {
    throw new Error("Build information response is incompatible.");
  }
  return parsed.data.data;
}

export function shortBuildSha(value: string): string {
  return value.toLowerCase() === "local" ? "local" : value.slice(0, 8);
}
