export type RiskTone = "error" | "info" | "success" | "warning";

export function riskTone(risk: string | null | undefined): RiskTone {
  const normalized = risk?.toLowerCase().replace(/_risk$/, "");
  if (normalized === "low") return "success";
  if (normalized === "medium") return "warning";
  if (normalized === "high") return "error";
  return "info";
}
