import { InlineAlert } from "@/components/ui";
import type { OCRReviewData, OCRTextFraudPreview } from "@/lib/ocr-client";

export function CompactOcrQualityBanner({
  status,
  evidenceQuality,
  warnings,
}: {
  status: OCRReviewData["status"];
  evidenceQuality: OCRTextFraudPreview["evidence_quality"];
  warnings: readonly string[];
}) {
  const readabilityWarnings = new Set([
    "OCR_ENGINE_UNAVAILABLE",
    "OCR_ENGINE_TIMEOUT",
    "OCR_ENGINE_FAILED",
    "CRITICAL_OCR_FIELDS_MISSING",
    "OCR_CONFIDENCE_LOW",
    "OCR_TEXT_EMPTY",
    "OCR_TEXT_SHORT",
  ]);
  const needsReview =
    status === "OCR_PARTIAL" ||
    warnings.some((warning) => readabilityWarnings.has(warning));

  if (!needsReview) return null;

  return (
    <InlineAlert
      tone="warning"
      title="Automatic reading needs review"
      message="Some visible text could not be read automatically. The original image is unchanged. The risk result below states this limitation."
    />
  );
}
