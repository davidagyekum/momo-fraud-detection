import { describe, expect, it, vi } from "vitest";
import {
  commitReferenceImport,
  listReferenceImports,
  statusTone,
  uploadReferenceImport,
  validateReferenceImport,
  type PortalRequester,
} from "./reference-imports";

describe("reference import client", () => {
  it("builds authenticated workflow requests without JSON-encoding the file", async () => {
    const request = vi.fn().mockResolvedValue({ data: {}, meta: {} });
    const typedRequest = request as PortalRequester;
    const file = new File(["provider_code"], "references.csv", {
      type: "text/csv",
    });

    await listReferenceImports(typedRequest);
    await uploadReferenceImport(
      typedRequest,
      "Controlled source",
      file,
      "upload-key-123",
    );
    await validateReferenceImport(typedRequest, "batch-1");
    await commitReferenceImport(typedRequest, "batch-1", "commit-key-123");

    expect(request).toHaveBeenNthCalledWith(
      1,
      "/admin/reference-imports?page_size=100",
    );
    expect(request).toHaveBeenNthCalledWith(
      2,
      "/admin/reference-imports",
      expect.objectContaining({
        body: expect.any(FormData) as FormData,
        headers: { "Idempotency-Key": "upload-key-123" },
      }),
    );
    expect(request).toHaveBeenNthCalledWith(
      3,
      "/admin/reference-imports/batch-1/validate",
      expect.objectContaining({ method: "POST" }),
    );
    expect(request).toHaveBeenNthCalledWith(
      4,
      "/admin/reference-imports/batch-1/commit",
      expect.objectContaining({
        headers: { "Idempotency-Key": "commit-key-123" },
      }),
    );
  });

  it("maps text-and-icon status tones independently from colour", () => {
    expect(statusTone("UPLOADED")).toBe("warning");
    expect(statusTone("VALIDATED")).toBe("info");
    expect(statusTone("COMMITTED")).toBe("success");
    expect(statusTone("FAILED")).toBe("danger");
  });
});
