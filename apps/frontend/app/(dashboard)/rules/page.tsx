import Link from "next/link";
import { getRules } from "@/lib/api";

const MODALITY_COLORS: Record<string, string> = {
  MUST: "bg-red-100 text-red-800",
  MUST_NOT: "bg-red-200 text-red-900",
  SHOULD: "bg-yellow-100 text-yellow-800",
  MAY: "bg-green-100 text-green-800",
  INFO: "bg-blue-100 text-blue-800",
};

const SEVERITY_COLORS: Record<string, string> = {
  CRITICAL: "bg-red-600 text-white",
  HIGH: "bg-orange-500 text-white",
  MEDIUM: "bg-yellow-500 text-white",
  LOW: "bg-gray-400 text-white",
};

export default async function RulesPage({
  searchParams,
}: {
  searchParams: Promise<{ page?: string }>;
}) {
  const params = await searchParams;
  const page = Number(params.page) || 1;
  let data;
  try {
    data = await getRules(page);
  } catch {
    data = null;
  }

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold">Rules</h1>
        <Link
          href="/rules/new"
          className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >
          New Rule
        </Link>
      </div>

      {!data ? (
        <p className="text-gray-500">
          Unable to connect to the backend. Is the server running?
        </p>
      ) : data.items.length === 0 ? (
        <p className="text-gray-500">No rules found. Create your first rule.</p>
      ) : (
        <>
          <div className="overflow-hidden rounded-lg border bg-white shadow-sm">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">
                    Statement
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">
                    Modality
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">
                    Severity
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">
                    Status
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">
                    Tags
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {data.items.map((rule) => (
                  <tr key={rule.id} className="hover:bg-gray-50">
                    <td className="max-w-md px-4 py-3">
                      <Link
                        href={`/rules/${rule.id}`}
                        className="text-sm text-blue-600 hover:underline"
                      >
                        {rule.statement.length > 120
                          ? `${rule.statement.slice(0, 120)}...`
                          : rule.statement}
                      </Link>
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${MODALITY_COLORS[rule.modality] ?? "bg-gray-100"}`}
                      >
                        {rule.modality}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${SEVERITY_COLORS[rule.severity] ?? "bg-gray-300"}`}
                      >
                        {rule.severity}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600">
                      {rule.status}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-1">
                        {rule.tags.map((tag) => (
                          <span
                            key={tag}
                            className="rounded bg-gray-100 px-1.5 py-0.5 text-xs text-gray-600"
                          >
                            {tag}
                          </span>
                        ))}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="mt-4 flex items-center justify-between text-sm text-gray-600">
            <span>
              Showing {(page - 1) * data.page_size + 1}–
              {Math.min(page * data.page_size, data.total)} of {data.total}
            </span>
            <div className="flex gap-2">
              {page > 1 && (
                <Link
                  href={`/rules?page=${page - 1}`}
                  className="rounded border px-3 py-1 hover:bg-gray-100"
                >
                  Previous
                </Link>
              )}
              {page * data.page_size < data.total && (
                <Link
                  href={`/rules?page=${page + 1}`}
                  className="rounded border px-3 py-1 hover:bg-gray-100"
                >
                  Next
                </Link>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
