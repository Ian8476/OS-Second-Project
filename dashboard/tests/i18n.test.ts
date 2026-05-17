import { describe, it, expect } from "vitest";
import { strings } from "@/shared/i18n/strings";

describe("i18n strings", () => {
  it("no string is empty", () => {
    for (const [key, value] of Object.entries(strings)) {
      expect(value, `key ${key} is empty`).toBeTruthy();
    }
  });

  it("contains required nav keys", () => {
    expect(strings["nav.cases"]).toBe("Casos");
    expect(strings["nav.monitoring"]).toBe("Monitoreo");
  });
});
