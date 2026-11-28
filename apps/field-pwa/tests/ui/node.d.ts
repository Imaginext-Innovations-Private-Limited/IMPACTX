// Minimal Node typings for the SW/manifest tests (no @types/node dependency).
declare module "node:fs" {
  export function readFileSync(path: string, enc: "utf8"): string;
  export function existsSync(path: string): boolean;
}
declare module "node:path" {
  export function resolve(...parts: string[]): string;
}
declare const __dirname: string;
