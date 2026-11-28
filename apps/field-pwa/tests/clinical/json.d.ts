// Ambient typing for JSON fixture imports in tests (tsconfig has no resolveJsonModule).
// Vitest/Vite resolves `*.json` imports natively at runtime.
declare module "*.json" {
  const value: unknown;
  export default value;
}
