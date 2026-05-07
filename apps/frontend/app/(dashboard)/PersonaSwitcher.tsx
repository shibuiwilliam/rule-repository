"use client";

import { createContext, useContext, useState, type ReactNode } from "react";

const PERSONAS = ["all", "compliance", "legal", "hr", "finance", "engineering", "sales", "executive"] as const;
export type Persona = (typeof PERSONAS)[number];

const PERSONA_LABELS: Record<Persona, string> = {
  all: "All Roles",
  compliance: "Compliance Officer",
  legal: "Legal Counsel",
  hr: "HR Manager",
  finance: "Finance Controller",
  engineering: "Engineering Lead",
  sales: "Sales Manager",
  executive: "Executive",
};

/** Which sidebar sections each persona sees. */
export const PERSONA_SECTIONS: Record<Persona, string[]> = {
  all: ["manage", "observe", "enforce", "settings"],
  compliance: ["manage", "observe", "enforce", "settings"],
  legal: ["manage", "observe", "settings"],
  hr: ["manage", "observe", "settings"],
  finance: ["manage", "observe", "settings"],
  engineering: ["manage", "observe", "enforce", "settings"],
  sales: ["manage", "observe", "settings"],
  executive: ["observe", "settings"],
};

// --- Context for sharing persona across components ---

const PersonaContext = createContext<{
  persona: Persona;
  setPersona: (p: Persona) => void;
}>({
  persona: "all",
  setPersona: () => {},
});

export function usePersona() {
  return useContext(PersonaContext);
}

export function PersonaProvider({ children }: { children: ReactNode }) {
  const [persona, setPersona] = useState<Persona>("all");
  return (
    <PersonaContext.Provider value={{ persona, setPersona }}>
      {children}
    </PersonaContext.Provider>
  );
}

export function PersonaSwitcher() {
  const { persona, setPersona } = usePersona();

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
