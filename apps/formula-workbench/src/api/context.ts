import type { ApiContext } from "./types";

const CONTEXT_FIELDS = [
  ["apiVersion"],
  ["referencePackage", "packageVersion"],
  ["referencePackage", "contentHash"],
  ["referencePackage", "publishedFormulaVersion"],
  ["referencePackage", "publishedFormulaDocumentHash"],
  ["formula", "schemaVersion"],
  ["formula", "formulaVersion"],
  ["formula", "documentHash"],
  ["season"],
  ["cohortSize"],
] as const;

type ContextPath = (typeof CONTEXT_FIELDS)[number];

function contextValue(context: ApiContext, path: ContextPath): unknown {
  let value: unknown = context;
  for (const segment of path) {
    if (typeof value !== "object" || value === null || !(segment in value)) {
      return undefined;
    }
    value = (value as Record<string, unknown>)[segment];
  }
  return value;
}

export function contextMismatches(expected: ApiContext, actual: ApiContext): string[] {
  return CONTEXT_FIELDS.filter(
    (path) => contextValue(expected, path) !== contextValue(actual, path),
  ).map((path) => path.join("."));
}

export function contextsEqual(expected: ApiContext, actual: ApiContext): boolean {
  return contextMismatches(expected, actual).length === 0;
}

export function contextFingerprint(context: ApiContext): string {
  return [
    context.apiVersion,
    context.referencePackage.packageVersion,
    context.referencePackage.contentHash,
    context.referencePackage.publishedFormulaVersion ?? "",
    context.referencePackage.publishedFormulaDocumentHash ?? "",
    context.formula.schemaVersion,
    context.formula.formulaVersion,
    context.formula.documentHash,
    context.season,
    context.cohortSize,
  ].join(":");
}

export class StaleContextError extends Error {
  readonly mismatches: string[];

  constructor(expected: ApiContext, actual: ApiContext) {
    const mismatches = contextMismatches(expected, actual);
    super(`API context changed: ${mismatches.join(", ") || "unknown context field"}.`);
    this.name = "StaleContextError";
    this.mismatches = mismatches;
  }
}

export function assertMatchingContext(expected: ApiContext, actual: ApiContext): void {
  if (!contextsEqual(expected, actual)) {
    throw new StaleContextError(expected, actual);
  }
}
