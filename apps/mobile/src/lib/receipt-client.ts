import type { ImagePickerAsset } from "expo-image-picker";
import { Platform } from "react-native";

import { ApiError } from "@/lib/api";
import type { Envelope } from "@/types/api";

const MAX_RECEIPT_BYTES = 10_485_760;
const ALLOWED_TYPES = new Set(["image/jpeg", "image/png", "image/webp"]);

export type ReceiptSource = "CAMERA" | "GALLERY";

export type SelectedReceipt = {
  asset: ImagePickerAsset;
  source: ReceiptSource;
  idempotencyKey: string;
  filename: string;
  mediaType: string;
};

export type ReceiptUploadData = {
  transaction: {
    id: string;
    status: "UPLOADED";
    created_at: string;
  };
  receipt: {
    id: string;
    media_type: string;
    size_bytes: number;
    dimensions: { width_px: number; height_px: number };
    quality: { score: number; warnings: string[] };
    duplicate_warning: {
      exact_match_found: boolean;
      near_match_found: boolean;
    };
    media: { thumbnail_url: string; original_url: string };
  };
  next_action: { type: "RUN_OCR"; endpoint: string };
  replayed: boolean;
};

type JsonRequest = <T>(path: string, init?: RequestInit) => Promise<T>;
type ResponseRequest = (path: string, init?: RequestInit) => Promise<Response>;

function randomIdempotencyKey(): string {
  const randomUuid = globalThis.crypto?.randomUUID?.();
  return randomUuid
    ? `receipt-${randomUuid}`
    : `receipt-${Date.now()}-${Math.random().toString(36).slice(2)}-${Math.random().toString(36).slice(2)}`;
}

function extensionFrom(value: string): string {
  const clean = value.split(/[?#]/, 1)[0] ?? "";
  const extension = clean.includes(".") ? clean.split(".").pop() : "";
  return extension?.toLowerCase() ?? "";
}

function typeFromExtension(extension: string): string | null {
  if (["jpg", "jpeg"].includes(extension)) return "image/jpeg";
  if (extension === "png") return "image/png";
  if (extension === "webp") return "image/webp";
  return null;
}

export function prepareReceipt(
  asset: ImagePickerAsset,
  source: ReceiptSource,
): SelectedReceipt {
  if (asset.type && asset.type !== "image") {
    throw new ApiError(
      "Select a still receipt image.",
      415,
      "INVALID_ASSET_TYPE",
    );
  }
  if (asset.fileSize && asset.fileSize > MAX_RECEIPT_BYTES) {
    throw new ApiError(
      "This receipt is larger than 10 MB. Choose a smaller image.",
      413,
      "RECEIPT_TOO_LARGE",
    );
  }
  if (asset.width < 1 || asset.height < 1) {
    throw new ApiError(
      "The selected receipt has invalid dimensions.",
      415,
      "RECEIPT_DIMENSIONS_INVALID",
    );
  }
  const extension = extensionFrom(asset.fileName ?? asset.uri);
  const mediaType = asset.mimeType ?? typeFromExtension(extension);
  if (!mediaType || !ALLOWED_TYPES.has(mediaType)) {
    throw new ApiError(
      "Choose a JPEG, PNG, or WebP receipt image.",
      415,
      "UNSUPPORTED_RECEIPT_FORMAT",
    );
  }
  const defaultExtension =
    mediaType === "image/jpeg" ? "jpg" : mediaType.replace("image/", "");
  const filename = asset.fileName ?? `receipt.${defaultExtension}`;
  if (typeFromExtension(extensionFrom(filename)) !== mediaType) {
    throw new ApiError(
      "The receipt filename does not match its image format.",
      415,
      "RECEIPT_EXTENSION_MISMATCH",
    );
  }
  return {
    asset,
    source,
    idempotencyKey: randomIdempotencyKey(),
    filename,
    mediaType,
  };
}

export async function uploadReceipt(
  request: JsonRequest,
  selected: SelectedReceipt,
): Promise<ReceiptUploadData> {
  const form = new FormData();
  if (selected.asset.file) {
    form.append("receipt", selected.asset.file, selected.filename);
  } else {
    form.append("receipt", {
      uri: selected.asset.uri,
      name: selected.filename,
      type: selected.mediaType,
    } as unknown as Blob);
  }
  form.append("source", selected.source);
  form.append(
    "client_metadata",
    JSON.stringify({ platform: Platform.OS, capture_ui: "expo-image-picker" }),
  );
  const response = await request<Envelope<ReceiptUploadData>>(
    "/api/v1/transactions",
    {
      method: "POST",
      headers: { "Idempotency-Key": selected.idempotencyKey },
      body: form,
    },
  );
  return response.data;
}

function bytesToBase64(bytes: Uint8Array): string {
  const alphabet =
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
  let output = "";
  for (let index = 0; index < bytes.length; index += 3) {
    const first = bytes[index] ?? 0;
    const second = bytes[index + 1];
    const third = bytes[index + 2];
    const combined = (first << 16) | ((second ?? 0) << 8) | (third ?? 0);
    output += alphabet[(combined >> 18) & 63];
    output += alphabet[(combined >> 12) & 63];
    output += second === undefined ? "=" : alphabet[(combined >> 6) & 63];
    output += third === undefined ? "=" : alphabet[combined & 63];
  }
  return output;
}

export async function fetchPrivateThumbnail(
  responseRequest: ResponseRequest,
  transactionId: string,
): Promise<string> {
  const response = await responseRequest(
    `/api/v1/transactions/${transactionId}/receipt?variant=thumbnail`,
    { headers: { Accept: "image/jpeg" } },
  );
  const mediaType = response.headers.get("Content-Type")?.split(";", 1)[0];
  if (mediaType !== "image/jpeg") {
    throw new ApiError(
      "The private receipt preview returned an unexpected format.",
      503,
      "RECEIPT_PREVIEW_INVALID",
    );
  }
  const content = new Uint8Array(await response.arrayBuffer());
  if (!content.length || content.length > 2_000_000) {
    throw new ApiError(
      "The private receipt preview could not be loaded safely.",
      503,
      "RECEIPT_PREVIEW_INVALID",
    );
  }
  return `data:image/jpeg;base64,${bytesToBase64(content)}`;
}
