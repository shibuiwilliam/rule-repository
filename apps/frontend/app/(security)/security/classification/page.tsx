"use client";

import { useState, useEffect } from "react";
import { fetchSeedData } from "@/lib/seed-data";

interface ClassificationLevel {
  level: string;
  color: string;
  description: string;
  ruleCount: number;
}

export default function ClassificationPage() {
  const [levels, setLevels] = useState<ClassificationLevel[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSeedData<{ classification_levels: ClassificationLevel[] }>("security").then((d) => {
      setLevels(d.classification_levels ?? []);
      setLoading(false);
    });
  }, []);

  if (loading) {
    return <div className="flex items-center justify-center py-12 text-sm text-gray-400">Loading...</div>;
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6 pb-12">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Data Classification</h1>
        <p className="mt-1 text-sm text-gray-500">
          Classification levels and their enforcement policies
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {levels.map((l) => (
          <div key={l.level} className={`rounded-xl border p-5 ${l.color}`}>
            <h3 className="text-lg font-bold">{l.level}</h3>
            <p className="mt-1 text-sm opacity-80">{l.description}</p>
            <p className="mt-3 text-2xl font-bold">{l.ruleCount}</p>
            <p className="text-xs opacity-70">rules at this level</p>
          </div>
        ))}
      </div>

      <div className="rounded-xl border bg-white p-5">
        <h2 className="text-base font-semibold text-gray-900">Enforcement Policy</h2>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="border-b bg-gray-50">
              <tr>
                <th className="px-4 py-2 font-medium text-gray-600">Level</th>
                <th className="px-4 py-2 font-medium text-gray-600">LLM Routing</th>
                <th className="px-4 py-2 font-medium text-gray-600">Log Retention</th>
                <th className="px-4 py-2 font-medium text-gray-600">Frontend Masking</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              <tr><td className="px-4 py-2 font-medium">PUBLIC</td><td className="px-4 py-2">Any provider</td><td className="px-4 py-2">Standard</td><td className="px-4 py-2">None</td></tr>
              <tr><td className="px-4 py-2 font-medium">INTERNAL</td><td className="px-4 py-2">Any provider</td><td className="px-4 py-2">Standard</td><td className="px-4 py-2">None</td></tr>
              <tr><td className="px-4 py-2 font-medium">CONFIDENTIAL</td><td className="px-4 py-2">Primary provider</td><td className="px-4 py-2">Standard</td><td className="px-4 py-2">Logs masked</td></tr>
              <tr><td className="px-4 py-2 font-medium">RESTRICTED</td><td className="px-4 py-2">Self-hosted only</td><td className="px-4 py-2">90-day purge</td><td className="px-4 py-2">Logs masked</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
