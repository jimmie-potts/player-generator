import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import { afterEach, describe, expect, it } from "vitest";

import { ComparisonModeTabs, type ComparisonMode } from "./ComparisonModeTabs";

afterEach(cleanup);

function TabsHarness({ initialMode = "tiers" }: { initialMode?: ComparisonMode }) {
  const [mode, setMode] = useState<ComparisonMode>(initialMode);
  return (
    <ComparisonModeTabs selectedMode={mode} onModeChange={setMode}>
      <p>{mode} content</p>
    </ComparisonModeTabs>
  );
}

describe("ComparisonModeTabs", () => {
  it("connects one active tab to its labelled tab panel", () => {
    render(<TabsHarness />);

    const tablist = screen.getByRole("tablist", { name: "Comparison player set" });
    const tierTab = screen.getByRole("tab", { name: "Tier sample" });
    const topTab = screen.getByRole("tab", { name: "Top 25" });
    const panel = screen.getByRole("tabpanel");

    expect(tablist).toBeTruthy();
    expect(tierTab.getAttribute("aria-selected")).toBe("true");
    expect(tierTab.tabIndex).toBe(0);
    expect(topTab.tabIndex).toBe(-1);
    expect(tierTab.getAttribute("aria-controls")).toBe(panel.id);
    expect(panel.getAttribute("aria-labelledby")).toBe(tierTab.id);
    expect(panel.textContent).toContain("tiers content");
    expect(document.getElementById(topTab.getAttribute("aria-controls")!)).toBeTruthy();
    expect(
      document.getElementById(
        screen.getByRole("tab", { name: "Custom list" }).getAttribute("aria-controls")!,
      ),
    ).toBeTruthy();
  });

  it("selects and focuses tabs with arrows, Home, and End", () => {
    render(<TabsHarness initialMode="top25" />);

    const tierTab = screen.getByRole("tab", { name: "Tier sample" });
    const topTab = screen.getByRole("tab", { name: "Top 25" });
    const customTab = screen.getByRole("tab", { name: "Custom list" });

    topTab.focus();
    fireEvent.keyDown(topTab, { key: "ArrowRight" });
    expect(customTab.getAttribute("aria-selected")).toBe("true");
    expect(document.activeElement).toBe(customTab);

    fireEvent.keyDown(customTab, { key: "ArrowRight" });
    expect(tierTab.getAttribute("aria-selected")).toBe("true");
    expect(document.activeElement).toBe(tierTab);

    fireEvent.keyDown(tierTab, { key: "End" });
    expect(customTab.getAttribute("aria-selected")).toBe("true");

    fireEvent.keyDown(customTab, { key: "Home" });
    expect(tierTab.getAttribute("aria-selected")).toBe("true");

    fireEvent.keyDown(tierTab, { key: "ArrowLeft" });
    expect(customTab.getAttribute("aria-selected")).toBe("true");
  });

  it("changes the active panel when a tab is clicked", () => {
    render(<TabsHarness />);

    fireEvent.click(screen.getByRole("tab", { name: "Custom list" }));

    expect(screen.getByRole("tab", { name: "Custom list" }).getAttribute("aria-selected")).toBe(
      "true",
    );
    expect(screen.getByRole("tabpanel").textContent).toContain("custom content");
  });
});
