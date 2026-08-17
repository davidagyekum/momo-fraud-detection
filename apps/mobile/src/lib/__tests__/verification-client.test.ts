import {
  verificationTone,
  verificationWarning,
} from "@/lib/verification-client";

test("verification labels and warnings remain explicit", () => {
  expect(verificationTone("VERIFIED")).toBe("success");
  expect(verificationTone("MISMATCH")).toBe("warning");
  expect(verificationTone("UNVERIFIED")).toBe("info");
  expect(verificationTone("NOT_ATTEMPTED")).toBe("info");
  expect(verificationWarning("RECEIPT_REUSED")).toContain("submitted before");
  expect(verificationWarning("UNKNOWN")).toContain("needs review");
});
