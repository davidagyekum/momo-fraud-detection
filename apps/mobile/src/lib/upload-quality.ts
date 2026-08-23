const warningLabels: Record<string, string> = {
  IMAGE_TOO_SMALL: "The image is small; automatic reading may need review.",
  LOW_CONTRAST: "The screenshot has low contrast.",
  POSSIBLY_BLURRY: "The screenshot may be blurry.",
  TOO_DARK: "The screenshot appears too dark.",
  TOO_BRIGHT: "The screenshot appears too bright.",
  POSSIBLE_EXACT_DUPLICATE:
    "This may be the same screenshot as an earlier upload.",
  POSSIBLE_NEAR_DUPLICATE:
    "This looks similar to an earlier screenshot. No other user's details are shown.",
};

export function uploadQualityMessages(
  warningCodes: readonly string[],
  duplicate: { exactMatchFound: boolean; nearMatchFound: boolean },
): string[] {
  const messages = warningCodes.map(
    (code) => warningLabels[code] ?? "The screenshot may need review.",
  );
  if (
    duplicate.exactMatchFound &&
    !warningCodes.includes("POSSIBLE_EXACT_DUPLICATE")
  ) {
    messages.push("This may be the same screenshot as an earlier upload.");
  }
  if (
    duplicate.nearMatchFound &&
    !warningCodes.includes("POSSIBLE_NEAR_DUPLICATE")
  ) {
    messages.push(
      "This looks similar to an earlier screenshot. No other user's details are shown.",
    );
  }
  return [...new Set(messages)];
}
