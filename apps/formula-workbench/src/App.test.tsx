import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { App } from "./App";

describe("App", () => {
  it("renders the formula workbench boundary", () => {
    const markup = renderToStaticMarkup(<App />);

    expect(markup).toContain("Formula Workbench");
    expect(markup).toContain("application boundary is ready");
  });
});
