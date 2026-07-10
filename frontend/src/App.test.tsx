import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi, afterEach } from "vitest";

vi.mock("./views/HomeView", () => ({ HomeView: () => <div>home-view</div> }));
vi.mock("./views/ImportView", () => ({
  ImportView: ({ bookId }: { bookId: string }) => <div>import-view:{bookId}</div>,
}));
vi.mock("./views/ChatView", () => ({
  ChatView: ({ bookId }: { bookId: string }) => <div>chat-view:{bookId}</div>,
}));

import App from "./App";

function withSearch(search: string, run: () => void) {
  window.history.pushState({}, "", `/${search}`);
  run();
}

afterEach(() => {
  vi.restoreAllMocks();
  window.history.pushState({}, "", "/");
});

describe("App routing", () => {
  it("renders HomeView when there is no view param", () => {
    withSearch("", () => render(<App />));
    expect(screen.getByText("home-view")).toBeInTheDocument();
  });

  it("renders ImportView with the book id when view=import", () => {
    withSearch("?view=import&book=ostep", () => render(<App />));
    expect(screen.getByText("import-view:ostep")).toBeInTheDocument();
  });

  it("renders ChatView with the book id when view=chat", () => {
    withSearch("?view=chat&book=civil-law", () => render(<App />));
    expect(screen.getByText("chat-view:civil-law")).toBeInTheDocument();
  });

  it("falls back to HomeView when view is import but book is missing", () => {
    withSearch("?view=import", () => render(<App />));
    expect(screen.getByText("home-view")).toBeInTheDocument();
  });
});
