// Writes dist/sw-version.js with a content hash of the built bundle so every
// rebuild changes the service-worker cache name (and the SW update check fires).
import { createHash } from "node:crypto";
import { readFileSync, writeFileSync } from "node:fs";

const h = createHash("sha256");
for (const f of ["dist/app.js", "dist/app.css", "index.html"]) h.update(readFileSync(f));
writeFileSync("dist/sw-version.js", `self.SW_BUILD = "${h.digest("hex").slice(0, 12)}";\n`);
