import { describe, expect, it } from "vitest";
import { edgeFromConnection, initialEdges, initialNodes, isSnapshot } from "./workflow";

describe("workflow graph helpers", () => {
  it("starts with a valid starter graph", () => {
    expect(initialNodes).toHaveLength(3);
    expect(initialEdges).toHaveLength(2);
    expect(isSnapshot({ nodes: initialNodes, edges: initialEdges })).toBe(true);
  });

  it("turns a YES or NO handle connection into a labelled edge", () => {
    const edge = edgeFromConnection({ source: "a", target: "b", sourceHandle: "YES", targetHandle: null });
    expect(edge?.label).toBe("YES");
    expect(edge?.data?.branch).toBe("YES");
  });

  it("rejects connections without an explicit branch handle", () => {
    expect(edgeFromConnection({ source: "a", target: "b", sourceHandle: null, targetHandle: null })).toBeNull();
  });
});
