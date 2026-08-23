const { readFileSync } = jest.requireActual("fs") as {
  readFileSync(path: string, encoding: "utf8"): string;
};
const { resolve } = jest.requireActual("path") as {
  resolve(...paths: string[]): string;
};

const ownerSources = [
  "src/app/(auth)/login.tsx",
  "src/app/(auth)/register.tsx",
  "src/app/(tabs)/home.tsx",
  "src/app/(tabs)/history.tsx",
  "src/app/(tabs)/notifications.tsx",
  "src/app/(tabs)/profile.tsx",
  "src/app/(tabs)/upload.tsx",
  "src/app/analysis/[analysisRunId].tsx",
  "src/app/ocr/[transactionId].tsx",
  "src/app/receipt/[transactionId].tsx",
  "src/app/transaction/[transactionId].tsx",
  "src/components/transaction-history.tsx",
].map((path) => readFileSync(resolve(".", path), "utf8"));

test.each([
  "Ready for your review",
  "Private image evidence",
  'label="Mark as read"',
  "Roles:",
  'label="Open transaction history"',
  'label="Open private receipt"',
])("removes owner-flow clutter: %s", (copy) => {
  expect(ownerSources.join("\n")).not.toContain(copy);
});

test.each([
  "Start a receipt check",
  "View receipt history",
  "Receipt details",
  "Receipt analysis",
  "Secure a receipt",
  "Add your receipt",
  "Take receipt photo",
  "Private receipt saved",
  "Secure another receipt",
  "Securely upload receipt",
])("does not present owner action copy as a receipt workflow: %s", (copy) => {
  expect(ownerSources.join("\n")).not.toContain(copy);
});
