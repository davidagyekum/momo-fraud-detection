import { resolveApiBaseUrl } from "../config";

describe("mobile API configuration", () => {
  it("uses the same-origin proxy for production web exports", () => {
    expect(resolveApiBaseUrl(undefined, "http://localhost:8000", true)).toBe(
      "",
    );
  });

  it("keeps an explicit release API URL and removes its trailing slash", () => {
    expect(
      resolveApiBaseUrl(
        "https://api.example.test/",
        "http://localhost:8000",
        true,
      ),
    ).toBe("https://api.example.test");
  });

  it("keeps the platform development URL outside production web", () => {
    expect(resolveApiBaseUrl(undefined, "http://10.0.2.2:8000", false)).toBe(
      "http://10.0.2.2:8000",
    );
  });
});
