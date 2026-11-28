/**
 * Tiny helpers that reproduce Python string formatting used by the clinical engine
 * so rationale / reminder text is byte-identical to `packages/clinical-engine`.
 */

/** Python `str(x)` / f-string `{x}` for the scalar values the engine interpolates. */
export function pyStr(value: number | string | null | undefined): string {
  if (value === null || value === undefined) return "None";
  return String(value);
}

/**
 * Python `f"{x:.1f}"`: correctly rounded on the exact binary value, ties to even.
 * JS `toFixed` agrees except on exact ties (e.g. 38.25), where it rounds away from zero.
 */
export function pyFixed1(value: number): string {
  const exact = Math.abs(value).toFixed(60);
  const dot = exact.indexOf(".");
  const tail = exact.slice(dot + 2);
  const isTie = /^50*$/.test(tail);
  if (!isTie) return value.toFixed(1);
  const lastDigit = Number(exact[dot + 1]);
  const truncated = exact.slice(0, dot + 2);
  if (lastDigit % 2 === 0) {
    return (value < 0 ? "-" : "") + truncated;
  }
  return value.toFixed(1);
}

/** Order-preserving de-duplication (Python `_dedupe_preserve_order`). */
export function dedupePreserveOrder(items: Iterable<string>): string[] {
  const seen = new Set<string>();
  const result: string[] = [];
  for (const item of items) {
    if (!seen.has(item)) {
      seen.add(item);
      result.push(item);
    }
  }
  return result;
}
