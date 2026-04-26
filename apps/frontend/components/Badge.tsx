/**
 * Reusable badge component for modality, severity, and status labels.
 */

const MODALITY_STYLES: Record<string, string> = {
  MUST: "bg-red-100 text-red-800",
  MUST_NOT: "bg-red-200 text-red-900",
  SHOULD: "bg-yellow-100 text-yellow-800",
  MAY: "bg-green-100 text-green-800",
  INFO: "bg-blue-100 text-blue-800",
};

const SEVERITY_STYLES: Record<string, string> = {
  CRITICAL: "bg-red-600 text-white",
  HIGH: "bg-orange-500 text-white",
  MEDIUM: "bg-yellow-500 text-white",
  LOW: "bg-gray-400 text-white",
};

const STATUS_STYLES: Record<string, string> = {
  DRAFT: "bg-gray-200 text-gray-700",
  REVIEW: "bg-purple-100 text-purple-800",
  APPROVED: "bg-blue-100 text-blue-800",
  EFFECTIVE: "bg-green-100 text-green-800",
  SUPERSEDED: "bg-orange-100 text-orange-800",
  RETIRED: "bg-gray-300 text-gray-600",
};

type BadgeVariant = "modality" | "severity" | "status" | "tag" | "relationship";

interface BadgeProps {
  label: string;
  variant?: BadgeVariant;
  className?: string;
}

function getStyle(variant: BadgeVariant, label: string): string {
  switch (variant) {
    case "modality":
      return MODALITY_STYLES[label] ?? "bg-gray-100 text-gray-800";
    case "severity":
      return SEVERITY_STYLES[label] ?? "bg-gray-300 text-gray-800";
    case "status":
      return STATUS_STYLES[label] ?? "bg-gray-100 text-gray-700";
    case "relationship":
      return "bg-purple-100 text-purple-800";
    case "tag":
    default:
      return "bg-gray-100 text-gray-600";
  }
}

export default function Badge({ label, variant = "tag", className = "" }: BadgeProps) {
  const style = getStyle(variant, label);
  return (
    <span
      className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${style} ${className}`}
    >
      {label}
    </span>
  );
}
