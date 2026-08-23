import { fetchBuildInfo, shortBuildSha } from "@/lib/build-info-client";
import { MOBILE_APP_VERSION } from "@/lib/app-build";

test("accepts the safe build identity contract", async () => {
  const request = jest.fn().mockResolvedValue({
    data: {
      application: "momo-fdvs-api",
      version: "0.1.0-test",
      build_commit: "0123456789abcdef",
      api_contract_version: "1.0.0",
      ocr_pipeline_version: "ocr-pipeline-v1",
      fraud_ruleset_version: "ghana-momo-hybrid-text-risk-v3",
      risk_policy_version: "analysis-risk-policy-demo-v4",
    },
    meta: { request_id: "request-id" },
  });

  const result = await fetchBuildInfo(request);

  expect(result.build_commit).toBe("0123456789abcdef");
  expect(request).toHaveBeenCalledWith("/api/v1/version");
});

test("presents the mobile app version and a short non-secret build identity", () => {
  expect(MOBILE_APP_VERSION).toBe("0.1.0");
  expect(shortBuildSha("0123456789abcdef")).toBe("01234567");
  expect(shortBuildSha("local")).toBe("local");
});

test("rejects extra fields that could expose private build data", async () => {
  const request = jest.fn().mockResolvedValue({
    data: {
      application: "momo-fdvs-api",
      version: "0.1.0",
      build_commit: "local",
      api_contract_version: "1.0.0",
      ocr_pipeline_version: "ocr-pipeline-v1",
      fraud_ruleset_version: "ghana-momo-hybrid-text-risk-v3",
      risk_policy_version: "analysis-risk-policy-demo-v4",
      private_path: "C:/private",
    },
    meta: {},
  });

  await expect(fetchBuildInfo(request)).rejects.toThrow(
    "Build information response is incompatible.",
  );
});
