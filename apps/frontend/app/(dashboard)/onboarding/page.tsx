"use client";

import { useState } from "react";

const TEMPLATES = [
  { id: "hr-attendance-jp", name: "HR Attendance (Japan)", domain: "HR", rules: 25 },
  { id: "contract-nda-standard", name: "NDA Review", domain: "Legal", rules: 15 },
  { id: "expense-claim-jp", name: "Expense Claims (Japan)", domain: "Finance", rules: 20 },
  { id: "bribery-anti-corruption", name: "Anti-Bribery", domain: "Compliance", rules: 18 },
  { id: "data-privacy-jp", name: "Data Privacy (Japan)", domain: "Compliance", rules: 18 },
  { id: "advertising-yakukiho", name: "Advertising (Japan)", domain: "Compliance", rules: 18 },
  { id: "python-fastapi", name: "Python + FastAPI", domain: "Engineering", rules: 15 },
  { id: "typescript-react", name: "TypeScript + React", domain: "Engineering", rules: 12 },
  { id: "security-owasp", name: "OWASP Security", domain: "Engineering", rules: 10 },
  { id: "api-design", name: "API Design", domain: "Engineering", rules: 10 },
  { id: "testing-standards", name: "Testing Standards", domain: "Engineering", rules: 10 },
];

export default function OnboardingPage() {
  const [step, setStep] = useState(1);
  const [selectedTemplates, setSelectedTemplates] = useState<string[]>([]);

  const toggleTemplate = (id: string) => {
    setSelectedTemplates((prev) =>
      prev.includes(id) ? prev.filter((t) => t !== id) : [...prev, id]
    );
  };

  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="text-2xl font-bold">Get Started</h1>
      <p className="mt-1 text-sm text-gray-500">
        Set up your rule repository in 3 steps
      </p>

      {/* Step indicators */}
      <div className="mt-8 flex gap-4">
        {[1, 2, 3].map((s) => (
          <div key={s} className="flex items-center gap-2">
            <div
              className={`flex h-8 w-8 items-center justify-center rounded-full text-sm font-bold ${
                s <= step
                  ? "bg-blue-600 text-white"
                  : "bg-gray-200 text-gray-500"
              }`}
            >
              {s}
            </div>
            <span className={`text-sm ${s <= step ? "text-gray-900" : "text-gray-400"}`}>
              {s === 1 && "Choose rules"}
              {s === 2 && "Upload documents"}
              {s === 3 && "Activate"}
            </span>
          </div>
        ))}
      </div>

      {/* Step 1: Select templates */}
      {step === 1 && (
        <div className="mt-8">
          <h2 className="text-lg font-semibold">
            What kind of rules do you want to manage?
          </h2>
          <p className="mt-1 text-sm text-gray-500">
            Choose one or more domain templates to get started with pre-built rules.
          </p>

          <div className="mt-6 grid grid-cols-2 gap-3">
            {TEMPLATES.map((t) => (
              <button
                key={t.id}
                onClick={() => toggleTemplate(t.id)}
                className={`rounded-lg border p-4 text-left transition ${
                  selectedTemplates.includes(t.id)
                    ? "border-blue-500 bg-blue-50"
                    : "border-gray-200 hover:border-gray-300"
                }`}
              >
                <div className="text-sm font-medium">{t.name}</div>
                <div className="mt-1 text-xs text-gray-500">
                  {t.domain} &middot; {t.rules} rules
                </div>
              </button>
            ))}
          </div>

          <div className="mt-6 flex justify-end">
            <button
              onClick={() => setStep(2)}
              disabled={selectedTemplates.length === 0}
              className="rounded-md bg-blue-600 px-6 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-40"
            >
              Next
            </button>
          </div>
        </div>
      )}

      {/* Step 2: Upload documents */}
      {step === 2 && (
        <div className="mt-8">
          <h2 className="text-lg font-semibold">
            Where are your existing rules?
          </h2>
          <p className="mt-1 text-sm text-gray-500">
            Upload policy documents, regulations, or handbooks. The extraction pipeline
            will propose candidate rules.
          </p>

          <div className="mt-6 rounded-lg border-2 border-dashed border-gray-300 p-12 text-center">
            <p className="text-sm text-gray-500">
              Drag and drop files here, or click to browse
            </p>
            <p className="mt-1 text-xs text-gray-400">
              PDF, DOCX, Markdown, or plain text
            </p>
          </div>

          <p className="mt-4 text-xs text-gray-400">
            You can also skip this step and upload documents later from the Documents page.
          </p>

          <div className="mt-6 flex justify-between">
            <button
              onClick={() => setStep(1)}
              className="rounded-md border px-6 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Back
            </button>
            <button
              onClick={() => setStep(3)}
              className="rounded-md bg-blue-600 px-6 py-2 text-sm font-medium text-white hover:bg-blue-700"
            >
              Next
            </button>
          </div>
        </div>
      )}

      {/* Step 3: Activate */}
      {step === 3 && (
        <div className="mt-8">
          <h2 className="text-lg font-semibold">
            Activate in shadow mode
          </h2>
          <p className="mt-1 text-sm text-gray-500">
            All rules start in shadow mode (experimental maturity). They produce
            NEEDS_CONFIRMATION instead of DENY, so you can observe without enforcing.
          </p>

          <div className="mt-6 rounded-lg border bg-green-50 p-6">
            <h3 className="font-medium text-green-800">Ready to activate</h3>
            <ul className="mt-2 space-y-1 text-sm text-green-700">
              <li>{selectedTemplates.length} template(s) selected</li>
              <li>All rules will start in shadow mode (experimental)</li>
              <li>No enforcement until you promote rules to stable</li>
              <li>You can review and adjust rules from the Rules page</li>
            </ul>
          </div>

          <div className="mt-6 flex justify-between">
            <button
              onClick={() => setStep(2)}
              className="rounded-md border px-6 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Back
            </button>
            <button
              onClick={() => {
                // TODO: Wire to POST /api/v1/rules/import for each selected template
                window.location.href = "/rules";
              }}
              className="rounded-md bg-green-600 px-6 py-2 text-sm font-medium text-white hover:bg-green-700"
            >
              Finish setup
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
