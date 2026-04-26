/**
 * Reusable rule summary card displayed in lists and search results.
 */

import Link from "next/link";
import Badge from "./Badge";

interface RuleCardProps {
  id: string;
  statement: string;
  modality: string;
  severity: string;
  status: string;
  tags: string[];
  score?: number;
}

export default function RuleCard({
  id,
  statement,
  modality,
  severity,
  status,
  tags,
  score,
}: RuleCardProps) {
  return (
    <div className="rounded-lg border bg-white p-4 shadow-sm hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between gap-4">
        <Link
          href={`/rules/${id}`}
          className="text-sm font-medium text-blue-600 hover:underline flex-1"
        >
          {statement.length > 200 ? `${statement.slice(0, 200)}...` : statement}
        </Link>
        {score !== undefined && (
          <span className="shrink-0 text-xs text-gray-400">
            score: {score.toFixed(3)}
          </span>
        )}
      </div>
      <div className="mt-2 flex flex-wrap gap-1.5">
        <Badge label={modality} variant="modality" />
        <Badge label={severity} variant="severity" />
        <Badge label={status} variant="status" />
        {tags.map((tag) => (
          <Badge key={tag} label={tag} variant="tag" />
        ))}
      </div>
    </div>
  );
}
