import { describe, expect, it } from "vitest";
import { riskTone } from "./risk-presentation";

describe("riskTone", () => {
  it.each([
    ["low", "success"],
    ["low_risk", "success"],
    ["medium", "warning"],
    ["medium_risk", "warning"],
    ["high", "error"],
    ["high_risk", "error"],
    ["inconclusive", "info"],
  ])("maps %s to %s", (risk, tone) => {
    expect(riskTone(risk)).toBe(tone);
  });
});
