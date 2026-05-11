"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";

export type PersonaId =
  | "engineering"
  | "hr"
  | "legal"
  | "compliance"
  | "security"
  | "finance"
  | "sales"
  | "marketing"
  | "admin";

export interface PersonaOption {
  id: PersonaId;
  label: string;
  description: string;
  icon: string;
  rootPath: string;
  color: string;
}

export const PERSONAS: PersonaOption[] = [
  {
    id: "engineering",
    label: "Engineering",
    description: "Code compliance, CI/CD rules, agent governance",
    icon: "\u2699\ufe0f",
    rootPath: "/dashboard",
    color: "bg-blue-50 text-blue-700 border-blue-200",
  },
  {
    id: "hr",
    label: "HR",
    description: "Attendance, leave, labor law compliance",
    icon: "\ud83d\udc65",
    rootPath: "/hr",
    color: "bg-indigo-50 text-indigo-700 border-indigo-200",
  },
  {
    id: "legal",
    label: "Legal",
    description: "Contract review, clause library, regulatory tracking",
    icon: "\u2696\ufe0f",
    rootPath: "/legal",
    color: "bg-slate-50 text-slate-700 border-slate-200",
  },
  {
    id: "compliance",
    label: "Compliance",
    description: "Bundles, audit packets, exception tracking",
    icon: "\ud83d\udee1\ufe0f",
    rootPath: "/compliance",
    color: "bg-amber-50 text-amber-700 border-amber-200",
  },
  {
    id: "security",
    label: "Security",
    description: "Classification, encryption, eval harness",
    icon: "\ud83d\udd12",
    rootPath: "/security",
    color: "bg-red-50 text-red-700 border-red-200",
  },
  {
    id: "finance",
    label: "Finance",
    description: "Expense policy, invoice validation, J-SOX controls",
    icon: "\ud83d\udcb0",
    rootPath: "/finance",
    color: "bg-emerald-50 text-emerald-700 border-emerald-200",
  },
  {
    id: "sales",
    label: "Sales",
    description: "Pricing approvals, discount governance, communication compliance",
    icon: "\ud83d\udcc8",
    rootPath: "/sales",
    color: "bg-orange-50 text-orange-700 border-orange-200",
  },
  {
    id: "marketing",
    label: "Marketing",
    description: "Creative review, ad compliance, brand rules",
    icon: "\ud83d\udce3",
    rootPath: "/marketing",
    color: "bg-purple-50 text-purple-700 border-purple-200",
  },
  {
    id: "admin",
    label: "Admin",
    description: "Tenants, users, system settings",
    icon: "\ud83d\udd27",
    rootPath: "/admin",
    color: "bg-gray-50 text-gray-700 border-gray-200",
  },
];

function detectCurrentPersona(pathname: string): PersonaOption {
  if (pathname.startsWith("/hr")) return PERSONAS.find((p) => p.id === "hr")!;
  if (pathname.startsWith("/legal")) return PERSONAS.find((p) => p.id === "legal")!;
  if (pathname.startsWith("/compliance")) return PERSONAS.find((p) => p.id === "compliance")!;
  if (pathname.startsWith("/security")) return PERSONAS.find((p) => p.id === "security")!;
  if (pathname.startsWith("/finance")) return PERSONAS.find((p) => p.id === "finance")!;
  if (pathname.startsWith("/sales")) return PERSONAS.find((p) => p.id === "sales")!;
  if (pathname.startsWith("/marketing")) return PERSONAS.find((p) => p.id === "marketing")!;
  if (pathname.startsWith("/admin")) return PERSONAS.find((p) => p.id === "admin")!;
  return PERSONAS.find((p) => p.id === "engineering")!;
}

export function PersonaSwitcher() {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const router = useRouter();
  const pathname = usePathname();
  const current = detectCurrentPersona(pathname);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  function handleSelect(persona: PersonaOption) {
    setOpen(false);
    if (persona.id !== current.id) {
      router.push(persona.rootPath);
    }
  }

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex w-full items-center gap-2 rounded-lg border bg-white px-3 py-2 text-sm font-medium text-gray-700 shadow-sm transition-colors hover:bg-gray-50"
        aria-expanded={open}
        aria-haspopup="listbox"
      >
        <span className="text-base">{current.icon}</span>
        <span className="flex-1 text-left">{current.label}</span>
        <svg
          className={`h-4 w-4 text-gray-400 transition-transform ${open ? "rotate-180" : ""}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {open && (
        <div
          className="absolute left-0 right-0 z-50 mt-1 max-h-96 overflow-y-auto rounded-lg border bg-white shadow-lg"
          role="listbox"
        >
          {PERSONAS.map((persona) => {
            const isActive = persona.id === current.id;
            return (
              <button
                key={persona.id}
                type="button"
                role="option"
                aria-selected={isActive}
                onClick={() => handleSelect(persona)}
                className={`flex w-full items-start gap-3 px-3 py-2.5 text-left transition-colors hover:bg-gray-50 ${
                  isActive ? "bg-gray-50" : ""
                }`}
              >
                <span className="mt-0.5 text-base">{persona.icon}</span>
                <div className="min-w-0 flex-1">
                  <p className={`text-sm font-medium ${isActive ? "text-blue-600" : "text-gray-900"}`}>
                    {persona.label}
                  </p>
                  <p className="text-xs text-gray-500">{persona.description}</p>
                </div>
                {isActive && (
                  <svg className="mt-1 h-4 w-4 text-blue-600" fill="currentColor" viewBox="0 0 20 20">
                    <path
                      fillRule="evenodd"
                      d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                      clipRule="evenodd"
                    />
                  </svg>
                )}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
