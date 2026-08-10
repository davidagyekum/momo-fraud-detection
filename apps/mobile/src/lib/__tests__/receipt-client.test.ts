import type { ImagePickerAsset } from "expo-image-picker";

import { ApiError } from "@/lib/api";
import {
  fetchPrivateThumbnail,
  prepareReceipt,
  uploadReceipt,
} from "@/lib/receipt-client";

function asset(overrides: Partial<ImagePickerAsset> = {}): ImagePickerAsset {
  return {
    uri: "file:///receipt.png",
    width: 640,
    height: 480,
    type: "image",
    fileName: "receipt.png",
    fileSize: 1024,
    mimeType: "image/png",
    ...overrides,
  };
}

test("prepares an accepted still image with a stable request key", () => {
  const selected = prepareReceipt(asset(), "GALLERY");
  expect(selected.filename).toBe("receipt.png");
  expect(selected.mediaType).toBe("image/png");
  expect(selected.idempotencyKey).toMatch(/^receipt-/);
});

test.each([
  [asset({ fileSize: 10_485_761 }), "RECEIPT_TOO_LARGE"],
  [asset({ width: 0 }), "RECEIPT_DIMENSIONS_INVALID"],
  [asset({ type: "video" }), "INVALID_ASSET_TYPE"],
  [
    asset({ fileName: "receipt.heic", mimeType: "image/heic" }),
    "UNSUPPORTED_RECEIPT_FORMAT",
  ],
  [asset({ fileName: "receipt.jpg" }), "RECEIPT_EXTENSION_MISMATCH"],
])("rejects an unsafe local selection", (input, code) => {
  expect(() => prepareReceipt(input, "GALLERY")).toThrow(
    expect.objectContaining({ code }),
  );
});

test("builds a multipart request without adding private device identifiers", async () => {
  const request = jest.fn().mockResolvedValue({
    data: {
      transaction: {
        id: "transaction-id",
        status: "UPLOADED",
        created_at: "now",
      },
      receipt: {
        id: "receipt-id",
        media_type: "image/png",
        size_bytes: 100,
        dimensions: { width_px: 640, height_px: 480 },
        quality: { score: 1, warnings: [] },
        duplicate_warning: {
          exact_match_found: false,
          near_match_found: false,
        },
        media: { thumbnail_url: "/thumbnail", original_url: "/original" },
      },
      next_action: { type: "RUN_OCR", endpoint: "/ocr" },
      replayed: false,
    },
    meta: {},
  });
  const result = await uploadReceipt(
    request,
    prepareReceipt(asset(), "GALLERY"),
  );
  expect(result.transaction.status).toBe("UPLOADED");
  expect(request).toHaveBeenCalledWith(
    "/api/v1/transactions",
    expect.objectContaining({
      method: "POST",
      headers: expect.objectContaining({
        "Idempotency-Key": expect.any(String),
      }),
      body: expect.any(FormData),
    }),
  );
  const requestText = JSON.stringify(request.mock.calls[0]);
  expect(requestText).not.toContain("assetId");
});

test("converts a protected JPEG response to a local preview URI", async () => {
  const responseRequest = jest.fn().mockResolvedValue({
    headers: new Headers({ "Content-Type": "image/jpeg" }),
    arrayBuffer: async () => new Uint8Array([255, 216, 255]).buffer,
  });
  await expect(
    fetchPrivateThumbnail(responseRequest, "transaction-id"),
  ).resolves.toBe("data:image/jpeg;base64,/9j/");
  expect(responseRequest).toHaveBeenCalledWith(
    "/api/v1/transactions/transaction-id/receipt?variant=thumbnail",
    { headers: { Accept: "image/jpeg" } },
  );
});

test("rejects a malformed private preview response", async () => {
  const responseRequest = jest.fn().mockResolvedValue({
    headers: new Headers({ "Content-Type": "text/html" }),
    arrayBuffer: async () => new ArrayBuffer(0),
  });
  await expect(
    fetchPrivateThumbnail(responseRequest, "transaction-id"),
  ).rejects.toBeInstanceOf(ApiError);
});
