import { afterEach, describe, expect, it, vi } from "vitest";

import { mockReport } from "./mock-data";
import { isUsableReport, loadReport } from "./loader";

const { source: _source, ...usableReport } = mockReport;

function stubFetch(payload: unknown, ok = true) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => ({ ok, json: async () => payload }) as Response),
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("isUsableReport", () => {
  it("accepts a report with methods and a comparison matrix", () => {
    expect(isUsableReport(usableReport)).toBe(true);
  });

  it("rejects a report with no methods", () => {
    expect(isUsableReport({ ...usableReport, methods: [] })).toBe(false);
  });

  it("rejects a report with no comparison rows", () => {
    expect(isUsableReport({ ...usableReport, comparison: [] })).toBe(false);
  });
});

describe("loadReport", () => {
  it("returns the fetched report tagged as bundle when usable", async () => {
    stubFetch(usableReport);

    const result = await loadReport();

    expect(result.source).toBe("bundle");
    expect(result.methods).toHaveLength(usableReport.methods.length);
    expect(result.comparison[0].id).toBe(usableReport.comparison[0].id);
  });

  it("falls back to the mock report when the fetch fails", async () => {
    stubFetch({}, false);

    const result = await loadReport();

    expect(result.source).toBe("mock");
    expect(result).toBe(mockReport);
  });

  it("falls back to the mock report when the payload is not usable", async () => {
    stubFetch({ ...usableReport, methods: [], comparison: [] });

    const result = await loadReport();

    expect(result.source).toBe("mock");
  });
});
