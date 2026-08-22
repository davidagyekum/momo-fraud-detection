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
  const needsReview =
    status === "OCR_PARTIAL" ||
    evidenceQuality !== "HIGH" ||
    warnings.length > 0;

  if (!needsReview) return null;

  return (
    <InlineAlert
      tone="warning"
      title="Automatic reading needs review"
      message="Some visible text could not be read automatically. The original image is unchanged. The risk result below states this limitation."
    />
  );
}
