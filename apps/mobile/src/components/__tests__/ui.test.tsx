import { act, fireEvent, render } from "@testing-library/react-native";

import {
  AppButton,
  EmptyState,
  InlineAlert,
  LabeledInput,
  PasswordInput,
} from "@/components/ui";

test("button exposes disabled and busy accessibility state", async () => {
  const onPress = jest.fn();
  const view = await render(
    <AppButton label="Save" onPress={onPress} loading />,
  );
  expect(
    view.getByRole("button", { name: "Save" }).props.accessibilityState,
  ).toEqual({ busy: true, disabled: true });
  fireEvent.press(view.getByRole("button", { name: "Save" }));
  expect(onPress).not.toHaveBeenCalled();
});

test("field renders its understandable validation error", async () => {
  const view = await render(
    <LabeledInput label="Email" error="Enter a valid email address." />,
  );
  expect(view.getByLabelText("Email")).toBeTruthy();
  expect(view.getByText("Enter a valid email address.")).toBeTruthy();
});

test("password visibility requires an explicit accessible action", async () => {
  const view = await render(<PasswordInput label="Password" />);
  await act(async () => {
    fireEvent.press(view.getByRole("button", { name: "Show password" }));
  });
  expect(view.getByRole("button", { name: "Hide password" })).toBeTruthy();
});

test("empty and alert states communicate without relying on colour", async () => {
  const view = await render(
    <>
      <InlineAlert
        tone="warning"
        title="Offline"
        message="Reconnect and retry."
      />
      <EmptyState title="No checks" message="Nothing is fabricated." />
    </>,
  );
  expect(view.getByText("Offline")).toBeTruthy();
  expect(view.getByText("No checks")).toBeTruthy();
});
