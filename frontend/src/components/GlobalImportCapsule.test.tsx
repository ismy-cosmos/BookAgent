import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { ProgressResponse } from "../api/types";
import { GlobalImportCapsule } from "./GlobalImportCapsule";

function busyProgress(): ProgressResponse {
  return {
    busy: true, reason: "ingesting", book_id: "ostep", pause_requested: false,
    progress: { stage: "parsing", current_file: 1, total_files: 3,
                current_image: null, total_images: null, current_filename: "ch01.pdf" },
    last_result: null,
  };
}

describe("GlobalImportCapsule", () => {
  it("renders nothing when not busy", () => {
    render(<GlobalImportCapsule progress={null} onPause={() => {}} />);
    expect(screen.queryByTestId("import-capsule")).not.toBeInTheDocument();
  });

  it("shows collapsed pill with percentage-ish stage text when busy", () => {
    render(<GlobalImportCapsule progress={busyProgress()} onPause={() => {}} />);
    expect(screen.getByTestId("import-capsule")).toBeInTheDocument();
    expect(screen.queryByText(/ostep/)).not.toBeInTheDocument();
  });

  it("expands to show book id, stage text and a pause button on click", async () => {
    const user = userEvent.setup();
    render(<GlobalImportCapsule progress={busyProgress()} onPause={() => {}} />);

    await user.click(screen.getByTestId("import-capsule"));

    expect(screen.getByText(/ostep/)).toBeInTheDocument();
    expect(screen.getByText(/解析中/)).toBeInTheDocument();
    expect(screen.getByText("暂停")).toBeInTheDocument();
  });

  it("collapses again on a second click", async () => {
    const user = userEvent.setup();
    render(<GlobalImportCapsule progress={busyProgress()} onPause={() => {}} />);

    const capsule = screen.getByTestId("import-capsule");
    await user.click(capsule);
    expect(screen.getByText("暂停")).toBeInTheDocument();
    await user.click(capsule);
    expect(screen.queryByText("暂停")).not.toBeInTheDocument();
  });

  it("clicking 暂停 calls onPause", async () => {
    const user = userEvent.setup();
    const onPause = vi.fn();
    render(<GlobalImportCapsule progress={busyProgress()} onPause={onPause} />);

    await user.click(screen.getByTestId("import-capsule"));
    await user.click(screen.getByText("暂停"));

    expect(onPause).toHaveBeenCalledOnce();
  });
});
