/**
 * Reusable pagination controls for list pages.
 */

import Link from "next/link";

interface PaginationProps {
  page: number;
  pageSize: number;
  total: number;
  baseUrl: string;
}

export default function Pagination({ page, pageSize, total, baseUrl }: PaginationProps) {
  const totalPages = Math.ceil(total / pageSize);
  const showingFrom = Math.min((page - 1) * pageSize + 1, total);
  const showingTo = Math.min(page * pageSize, total);

  if (total === 0) return null;

  return (
    <div className="mt-4 flex items-center justify-between text-sm text-gray-600">
      <span>
        Showing {showingFrom}–{showingTo} of {total}
      </span>
      <div className="flex gap-2">
        {page > 1 && (
          <Link
            href={`${baseUrl}?page=${page - 1}`}
            className="rounded border px-3 py-1 hover:bg-gray-100"
          >
            Previous
          </Link>
        )}
        <span className="px-2 py-1 text-gray-400">
          {page} / {totalPages}
        </span>
        {page < totalPages && (
          <Link
            href={`${baseUrl}?page=${page + 1}`}
            className="rounded border px-3 py-1 hover:bg-gray-100"
          >
            Next
          </Link>
        )}
      </div>
    </div>
  );
}
