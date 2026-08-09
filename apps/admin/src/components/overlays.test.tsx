import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { Dialog, Drawer } from "./overlays";

describe("accessible overlays", () => {
  it("labels a dialog and closes it with Escape", async () => {
    const user = userEvent.setup();
    const close = vi.fn();
    render(
      <Dialog open title="Confirm action" onClose={close}>
        <button>Continue</button>
      </Dialog>,
    );
    expect(
      screen.getByRole("dialog", { name: "Confirm action" }),
    ).toBeInTheDocument();
    await user.keyboard("{Escape}");
    expect(close).toHaveBeenCalledOnce();
  });

  it("renders a modal navigation drawer", () => {
    render(
      <Drawer open title="Navigation" onClose={() => undefined}>
        <a href="/dashboard">Dashboard</a>
      </Drawer>,
    );
    expect(screen.getByRole("dialog", { name: "Navigation" })).toHaveAttribute(
      "aria-modal",
      "true",
    );
  });

  it("contains keyboard focus inside a dialog", async () => {
    const user = userEvent.setup();
    render(
      <Dialog open title="Focus boundary" onClose={() => undefined}>
        <button>First action</button>
        <button>Last action</button>
      </Dialog>,
    );
    expect(
      screen.getByRole("button", { name: "Close Focus boundary" }),
    ).toHaveFocus();
    await user.keyboard("{Shift>}{Tab}{/Shift}");
    expect(screen.getByRole("button", { name: "Last action" })).toHaveFocus();
    await user.keyboard("{Tab}");
    expect(
      screen.getByRole("button", { name: "Close Focus boundary" }),
    ).toHaveFocus();
  });
});
