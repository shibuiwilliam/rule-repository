"use client";

import { useEffect, useState } from "react";

interface Department {
  id: string;
  name: string;
  type: string;
  head: string;
}

export default function DepartmentsPage() {
  const [departments, setDepartments] = useState<Department[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchDepartments = async () => {
      try {
        const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
        const resp = await fetch(`${apiBase}/api/v1/departments`);
        if (resp.ok) {
          const data = await resp.json();
          setDepartments(data.departments || data || []);
        }
      } catch {
        // Handle fetch error silently in dev
      } finally {
        setLoading(false);
      }
    };
    fetchDepartments();
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Department Management</h1>
        <p className="text-sm text-gray-500">
          Manage departments, memberships, and rule ownership
        </p>
      </div>

      {loading ? (
        <p className="text-gray-400">Loading...</p>
      ) : (
        <div className="overflow-x-auto rounded-lg border">
          <table className="w-full text-left text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3">Department</th>
                <th className="px-4 py-3">Type</th>
                <th className="px-4 py-3">Head</th>
                <th className="px-4 py-3">Actions</th>
              </tr>
            </thead>
            <tbody>
              {departments.length === 0 ? (
                <tr>
                  <td colSpan={4} className="px-4 py-8 text-center text-gray-400">
                    No departments configured. Use the API to create departments.
                  </td>
                </tr>
              ) : (
                departments.map((dept) => (
                  <tr key={dept.id} className="border-t">
                    <td className="px-4 py-3 font-medium">{dept.name}</td>
                    <td className="px-4 py-3">
                      <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs capitalize">
                        {dept.type}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-500">{dept.head || "—"}</td>
                    <td className="px-4 py-3">
                      <button className="text-xs text-blue-600 hover:underline">
                        Manage Members
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
