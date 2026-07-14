import { describe, expect, it } from "vitest";

import { formatNumber, formatPercent, formatSignedNumber, identifierLabel } from "./format";

describe("display formatting", () => {
  it("turns contract identifiers into plain safe labels", () => {
    expect(identifierLabel("threePointShooting")).toBe("Three Point Shooting");
    expect(identifierLabel("all_star<script>")).toBe("All Star Script");
    expect(identifierLabel("---")).toBe("Unnamed");
  });

  it("formats finite values and distinguishes unavailable numbers", () => {
    expect(formatNumber(12.34567)).toMatch(/12[.,]346/);
    expect(formatSignedNumber(2)).toContain("+2");
    expect(formatSignedNumber(0)).toBe("0");
    expect(formatSignedNumber(0.000001)).toBe("+<0.0001");
    expect(formatSignedNumber(-0.000001)).toBe("−<0.0001");
    expect(formatPercent(0.875)).toMatch(/87[.,]5/);
    expect(formatNumber(null)).toBe("—");
    expect(formatNumber(Number.NaN)).toBe("—");
  });
});
