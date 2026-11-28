import { describe, expect, it } from "vitest";
import { IMNCI_PEDIATRIC_RULES, MATERNAL_ANC_RULES, UIP_VACCINE_RULES } from "../../src/clinical";
import imnciSource from "../../../../packages/clinical-engine/rules/imnci_pediatric.json";
import maternalSource from "../../../../packages/clinical-engine/rules/maternal_anc.json";
import uipSource from "../../../../packages/clinical-engine/rules/uip_vaccines.json";

// Guards against drift: bundled offline rule tables must equal the source JSON exactly.
describe("bundled rule tables are exact copies of packages/clinical-engine/rules", () => {
  it("imnci_pediatric", () => expect(IMNCI_PEDIATRIC_RULES).toStrictEqual(imnciSource));
  it("maternal_anc", () => expect(MATERNAL_ANC_RULES).toStrictEqual(maternalSource));
  it("uip_vaccines", () => expect(UIP_VACCINE_RULES).toStrictEqual(uipSource));
});
