"use client";

import { useState } from "react";

const PERSONAS = ["all", "compliance", "engineering", "operator"] as const;
type Persona = (typeof PERSONAS)[number];

const PERSONA_LABELS: Record<Persona, string> = {
  all: "All",
  compliance: "Compliance",
  engineering: "Engineering",
  operator: "AI Operator",
};

export function PersonaSwitcher() {
  const [persona, setPersona] = useState<Persona>("all");

  return (
    <div className="mt-4">
      <label
        htmlFor="persona-select"
        className="mb-1 block px-1 text-xs font-semibold uppercase tracking-wider text-gray-400"
      >
        Persona
      </label>
      <select
        id="persona-select"
        value={persona}
        onChange={(e) => setPersona(e.target.value as Persona)}
        className="w-full rounded-md border bg-white px-3 py-1.5 text-sm text-gray-700"
        title="Switch persona to filter sidebar sections relevant to your role"
      >
        {PERSONAS.map((p) => (
          <option key={p} value={p}>
            {PERSONA_LABELS[p]}
          </option>
        ))}
      </select>
    </div>
  );
}
