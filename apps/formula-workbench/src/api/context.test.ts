import { describe, expect, it } from "vitest";

import {
  assertMatchingContext,
  contextFingerprint,
  contextMismatches,
  contextsEqual,
  StaleContextError,
} from "./context";
import type { ApiContext } from "./types";

function context(): ApiContext {
  return {
    apiVersion: "1",
    referencePackage: {
      packageVersion: 2,
      contentHash: "a".repeat(64),
      publishedFormulaVersion: "1.0.0",
      publishedFormulaDocumentHash: "b".repeat(64),
    },
    formula: {
      schemaVersion: 1,
      formulaVersion: "1.0.0",
      documentHash: "b".repeat(64),
    },
    season: 2026,
    cohortSize: 582,
  };
}

describe("API context identity", () => {
  it("matches independently deserialized contexts with every identity field equal", () => {
    const expected = context();
    const actual = structuredClone(expected);

    expect(contextsEqual(expected, actual)).toBe(true);
    expect(contextMismatches(expected, actual)).toEqual([]);
    expect(contextFingerprint(expected)).toBe(contextFingerprint(actual));
    expect(() => assertMatchingContext(expected, actual)).not.toThrow();
  });

  it("identifies every changed context field and rejects stale data", () => {
    const expected = context();
    const actual = context();
    actual.referencePackage.contentHash = "c".repeat(64);
    actual.formula.documentHash = "d".repeat(64);
    actual.season = 2025;

    expect(contextsEqual(expected, actual)).toBe(false);
    expect(contextMismatches(expected, actual)).toEqual([
      "referencePackage.contentHash",
      "formula.documentHash",
      "season",
    ]);
    expect(() => assertMatchingContext(expected, actual)).toThrow(StaleContextError);

    try {
      assertMatchingContext(expected, actual);
    } catch (error) {
      expect(error).toMatchObject({
        name: "StaleContextError",
        mismatches: [
          "referencePackage.contentHash",
          "formula.documentHash",
          "season",
        ],
      });
    }
  });
});
