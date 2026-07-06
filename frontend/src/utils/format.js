/**
 * format.js
 * =========
 * Single source of truth for currency display. Was previously hardcoded
 * as "$" in 13+ files across the frontend -- now every price goes through
 * this one function, so changing the currency again means editing one
 * line instead of hunting through the whole codebase.
 */
export function formatPrice(value) {
  const num = Number(value) || 0
  return `₪${num.toFixed(2)}`
}
