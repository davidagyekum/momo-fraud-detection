import { describe, expect, it } from "vitest";
import { readCookie } from "./cookies";

describe("readCookie", () => {
  it("returns and decodes the named cookie", () => {
    expect(
      readCookie(
        "momo_fdvs_csrf",
        "theme=dark; momo_fdvs_csrf=a%2Bb%3D; other=1",
      ),
    ).toBe("a+b=");
  });

  it("does not use a cookie with a partial name", () => {
    expect(readCookie("token", "long_token=secret; tokenish=nope")).toBeNull();
  });
});
