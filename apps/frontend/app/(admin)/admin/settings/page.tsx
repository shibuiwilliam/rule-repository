"use client";

const FEATURE_FLAGS = [
  { key: "EVALUATION_SUBJECT_V2_ENABLED", value: true, description: "Surface-aware evaluation engine" },
  { key: "STRUCTURED_SCOPE_ENABLED", value: true, description: "Multi-axis structured scope filtering" },
  { key: "RULE_KIND_POLYMORPHISM_ENABLED", value: true, description: "Deterministic evaluation for computational/procedural rules" },
  { key: "DOMAIN_PACKS_ENABLED", value: true, description: "Domain pack loader at startup" },
  { key: "HYBRID_EVALUATION_ENABLED", value: true, description: "Deterministic + LLM hybrid evaluation" },
  { key: "PERSONA_ROUTING_ENABLED", value: true, description: "Persona-specific frontend routing" },
  { key: "ABAC_GOVERNANCE_ENABLED", value: false, description: "Attribute-based access control policies" },
  { key: "MARKETPLACE_ENABLED", value: false, description: "Rule marketplace (deferred)" },
  { key: "GATEWAY_EXTERNAL_INTAKE_ENABLED", value: false, description: "External webhook ingress (deferred)" },
];

export default function SettingsPage() {
  return (
    <div className="mx-auto max-w-5xl space-y-6 pb-12">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">System Settings</h1>
        <p className="mt-1 text-sm text-gray-500">Feature flags, LLM configuration, and system parameters</p>
      </div>

      <div className="rounded-xl border bg-white p-5">
        <h2 className="text-base font-semibold text-gray-900">LLM Configuration</h2>
        <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div className="rounded-lg border p-4">
            <p className="text-xs font-semibold uppercase text-gray-400">Default Model</p>
            <p className="mt-1 font-mono text-sm text-gray-900">gemini-3-flash-preview</p>
          </div>
          <div className="rounded-lg border p-4">
            <p className="text-xs font-semibold uppercase text-gray-400">Judge Model</p>
            <p className="mt-1 font-mono text-sm text-gray-900">gemini-3.1-pro-preview</p>
          </div>
        </div>
      </div>

      <div className="rounded-xl border bg-white">
        <div className="border-b px-5 py-4">
          <h2 className="text-base font-semibold text-gray-900">Feature Flags</h2>
        </div>
        <div className="divide-y">
          {FEATURE_FLAGS.map((f) => (
            <div key={f.key} className="flex items-center justify-between px-5 py-3">
              <div>
                <p className="font-mono text-sm text-gray-900">{f.key}</p>
                <p className="text-xs text-gray-500">{f.description}</p>
              </div>
              <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${f.value ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                {f.value ? "enabled" : "disabled"}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
