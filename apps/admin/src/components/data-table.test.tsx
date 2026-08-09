import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import {
  DataTable,
  FilterBar,
  Pagination,
  type DataColumn,
} from "./data-table";

interface Row {
  id: string;
  label: string;
}

const columns: DataColumn<Row>[] = [
  { id: "label", header: "Label", cell: (row) => row.label },
];

describe("DataTable", () => {
  it("renders semantic table and compact alternatives", () => {
    render(
      <DataTable
        caption="Safe records"
        columns={columns}
        rows={[{ id: "one", label: "Masked record" }]}
        rowKey={(row) => row.id}
        emptyTitle="Empty"
        emptyDescription="No records."
      />,
    );
    expect(
      screen.getByRole("table", { name: "Safe records" }),
    ).toBeInTheDocument();
    expect(
      screen.getByLabelText("Safe records compact view"),
    ).toHaveTextContent("Masked record");
  });

  it("renders an honest empty state instead of placeholder rows", () => {
    render(
      <DataTable
        caption="Safe records"
        columns={columns}
        rows={[]}
        rowKey={(row) => row.id}
        emptyTitle="No data available"
        emptyDescription="Operational data will be available later."
      />,
    );
    expect(screen.getByRole("status")).toHaveTextContent("No data available");
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });

  it("exposes keyboard-operable filters and pagination", async () => {
    const user = userEvent.setup();
    const openFilters = vi.fn();
    const changePage = vi.fn();
    render(
      <>
        <FilterBar onOpenFilters={openFilters}>Active filters</FilterBar>
        <Pagination page={2} pageCount={3} onPageChange={changePage} />
      </>,
    );
    await user.click(screen.getByRole("button", { name: "Filters" }));
    await user.click(screen.getByRole("button", { name: "Previous" }));
    await user.click(screen.getByRole("button", { name: "Next" }));
    expect(openFilters).toHaveBeenCalledOnce();
    expect(changePage).toHaveBeenNthCalledWith(1, 1);
    expect(changePage).toHaveBeenNthCalledWith(2, 3);
    expect(screen.getByText("Page 2 of 3")).toBeInTheDocument();
  });

  it("disables pagination at both boundaries", () => {
    const { rerender } = render(
      <Pagination page={1} pageCount={1} onPageChange={() => undefined} />,
    );
    expect(screen.getByRole("button", { name: "Previous" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Next" })).toBeDisabled();
    rerender(
      <Pagination page={1} pageCount={0} onPageChange={() => undefined} />,
    );
    expect(screen.getByText("Page 1 of 1")).toBeInTheDocument();
  });
});
