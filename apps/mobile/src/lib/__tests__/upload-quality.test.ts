import { uploadQualityMessages } from "@/lib/upload-quality";

test("combines distinct image and duplicate warnings into one message list", () => {
  expect(
    uploadQualityMessages(
      ["LOW_CONTRAST", "POSSIBLY_BLURRY", "POSSIBLE_EXACT_DUPLICATE"],
      { exactMatchFound: true, nearMatchFound: false },
    ),
  ).toEqual([
    "The screenshot has low contrast.",
    "The screenshot may be blurry.",
    "This may be the same screenshot as an earlier upload.",
  ]);
});

test("adds one duplicate note when the server flag has no warning code", () => {
  expect(
    uploadQualityMessages([], {
      exactMatchFound: false,
      nearMatchFound: true,
    }),
  ).toEqual([
    "This looks similar to an earlier screenshot. No other user's details are shown.",
  ]);
});
