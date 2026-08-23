import { render } from "@testing-library/react-native";

import { CompactOcrQualityBanner } from "@/components/ocr-quality-banner";

test("consolidates partial OCR and multiple warning codes into one notice", async () => {
  const view = await render(
    <CompactOcrQualityBanner
      status="OCR_PARTIAL"
      evidenceQuality="LOW"
      warnings={[
        "CRITICAL_OCR_FIELDS_MISSING",
        "UNKNOWN_TEMPLATE_GENERIC_FALLBACK",
      ]}
    />,
  );

  expect(view.getAllByText("Automatic reading needs review")).toHaveLength(1);
  expect(
    view.getByText(
      "Some visible text could not be read automatically. The original image is unchanged. The risk result below states this limitation.",
    ),
  ).toBeTruthy();
});

test("does not add a warning for a clean readable result", async () => {
  const view = await render(
    <CompactOcrQualityBanner
      status="OCR_READY"
      evidenceQuality="HIGH"
      warnings={[]}
    />,
  );

  expect(view.queryByText("Automatic reading needs review")).toBeNull();
});

test("does not call a non-readability warning unreadable text", async () => {
  const view = await render(
    <CompactOcrQualityBanner
      status="OCR_READY"
      evidenceQuality="LOW"
      warnings={["UNKNOWN_TEMPLATE_GENERIC_FALLBACK"]}
    />,
  );

  expect(view.queryByText("Automatic reading needs review")).toBeNull();
  expect(view.queryByText(/could not be read automatically/i)).toBeNull();
});
