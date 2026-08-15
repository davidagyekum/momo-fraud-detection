import { fireEvent, render } from "@testing-library/react-native";

import { TransactionHistoryView } from "@/components/transaction-history";
import type { TransactionSummary } from "@/types/history";

test("renders an honest empty state", async () => {
  const view = await render(
    <TransactionHistoryView items={[]} onOpen={jest.fn()} />,
  );
  expect(view.getByText("No receipt checks found")).toBeTruthy();
});

test("renders persisted statuses and opens the selected owner transaction", async () => {
  const onOpen = jest.fn();
  const item = {
    id: "tx-1",
    status: "PARTIAL",
    provider_code: "MTN",
    display_reference_masked: "***1234",
    created_at: "2026-08-15T12:00:00Z",
    updated_at: "2026-08-15T12:00:01Z",
    thumbnail_url: null,
    owner_visible: true,
    latest_analysis: {
      id: "run-1",
      status: "PARTIAL",
      band: "inconclusive",
      class: null,
      score: null,
      verification_status: "MISMATCH",
      completed_at: "2026-08-15T12:00:01Z",
      policy_version: "risk-policy-v1",
    },
  } as TransactionSummary;
  const view = await render(
    <TransactionHistoryView items={[item]} onOpen={onOpen} />,
  );
  expect(view.getByText("MTN receipt")).toBeTruthy();
  expect(view.getByLabelText("Status: Risk: Inconclusive")).toBeTruthy();
  expect(view.getByLabelText("Status: Verification: Mismatch")).toBeTruthy();
  fireEvent.press(view.getByRole("button", { name: "Open receipt details" }));
  expect(onOpen).toHaveBeenCalledWith("tx-1");
});
