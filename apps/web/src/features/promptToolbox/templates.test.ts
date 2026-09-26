import { describe, expect, it } from "vitest";

import { promptDestinations, studyPromptTemplates } from "./templates";

describe("study prompt template registry", () => {
  it("keeps templates and external destinations explicit and versioned", () => {
    expect(studyPromptTemplates).toHaveLength(4);
    expect(new Set(studyPromptTemplates.map((template) => template.id)).size).toBe(4);
    expect(
      studyPromptTemplates.every((template) => /^study-prompt-v\d+\.\d+\.\d+$/.test(template.version)),
    ).toBe(true);
    expect(promptDestinations.every((destination) => destination.url.startsWith("https://"))).toBe(
      true,
    );
  });
});

