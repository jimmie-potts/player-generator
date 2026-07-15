const DEFAULT_NUMBER_FORMAT = new Intl.NumberFormat(undefined, {
  maximumFractionDigits: 3,
});

const SIGNED_NUMBER_FORMAT = new Intl.NumberFormat(undefined, {
  maximumFractionDigits: 4,
  signDisplay: "always",
});

const PERCENT_FORMAT = new Intl.NumberFormat(undefined, {
  maximumFractionDigits: 1,
  style: "percent",
});

export function identifierLabel(value: string): string {
  const words = value
    .replace(/([a-z0-9])([A-Z])/g, "$1 $2")
    .replace(/[^A-Za-z0-9]+/g, " ")
    .trim()
    .split(/\s+/)
    .filter(Boolean);
  if (!words.length) {
    return "Unnamed";
  }
  return words
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(" ");
}

export function formatNumber(value: unknown): string {
  return typeof value === "number" && Number.isFinite(value)
    ? DEFAULT_NUMBER_FORMAT.format(value)
    : "—";
}

export function formatSignedNumber(value: unknown): string {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return "—";
  }
  if (value === 0) {
    return DEFAULT_NUMBER_FORMAT.format(0);
  }
  if (Math.abs(value) < 0.00005) {
    return value > 0 ? "+<0.0001" : "−<0.0001";
  }
  return SIGNED_NUMBER_FORMAT.format(value);
}

export function formatPercent(value: unknown): string {
  return typeof value === "number" && Number.isFinite(value)
    ? PERCENT_FORMAT.format(value)
    : "—";
}
