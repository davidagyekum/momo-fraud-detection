import {
  analysisRecordLabel,
  readableAnalysisStatus,
  readableProviderName,
} from "@/lib/analysis-presentation";

test("uses a clear label for screenshot-only records", () => {
  expect(analysisRecordLabel("PARTIAL", "NOT_REQUIRED")).toBe(
    "Screenshot-only analysis",
  );
});

test("turns internal status values into readable text", () => {
  expect(readableAnalysisStatus("NOT_ATTEMPTED")).toBe("Not attempted");
  expect(readableAnalysisStatus("HIGH_RISK")).toBe("High risk");
  expect(readableAnalysisStatus(null)).toBe("Not available");
});

test("turns provider codes into readable receipt names", () => {
  expect(readableProviderName("TELECEL_CASH")).toBe("Telecel Cash");
  expect(readableProviderName("MTN_MOMO")).toBe("MTN MoMo");
  expect(readableProviderName(null)).toBe("Receipt");
});
