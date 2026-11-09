// Generates lib/types.ts from lib/schema.json (exported from the Pydantic models).
// Run: npm run gen:types   (CI fails if the committed file is stale)
import { readFileSync, writeFileSync } from "node:fs";
import { compile } from "json-schema-to-typescript";

const schema = JSON.parse(readFileSync(new URL("../lib/schema.json", import.meta.url), "utf8"));

// Pydantic puts a `title` on every property, which json-schema-to-typescript turns into a named alias
// per field (Symbol1, Title2, ...). Keep titles only on the top-level $defs. Also drop siblings of
// `$ref` (e.g. a field description), which would otherwise clone the referenced type (Citation1).
function clean(node, isDef = false) {
  if (Array.isArray(node)) return node.forEach((n) => clean(n));
  if (!node || typeof node !== "object") return;
  if (node.$ref) for (const k of Object.keys(node)) if (k !== "$ref") delete node[k];
  if (!isDef) delete node.title;
  for (const [k, v] of Object.entries(node)) {
    if (k === "$defs") for (const d of Object.values(v)) clean(d, true);
    else if (k === "properties") for (const prop of Object.values(v)) clean(prop);
    else clean(v);
  }
}
clean(schema);
// Give every definition a reachable root so all of them are emitted; use each def's title as its name.
schema.type = "object";
schema.properties = Object.fromEntries(Object.keys(schema.$defs).map((k) => [k, { $ref: `#/$defs/${k}` }]));
schema.additionalProperties = false;

let ts = await compile(schema, "FinnContracts", {
  bannerComment:
    "/* AUTO-GENERATED from backend/finn/models (Pydantic) — do not edit by hand.\n" +
    " * Regenerate: npm run gen:types */",
  additionalProperties: false,
  enableConstEnums: false,
  inferStringEnumKeysFromValues: false,
  strictIndexSignatures: true,
  style: { singleQuote: false, semi: true, printWidth: 110 },
});
// The synthetic root interface only exists to make every $def reachable — drop it.
ts = ts.replace(/export interface FinnContracts \{[\s\S]*?\n\}\n/, "");
writeFileSync(new URL("../lib/types.ts", import.meta.url), ts);
console.log("wrote lib/types.ts");
