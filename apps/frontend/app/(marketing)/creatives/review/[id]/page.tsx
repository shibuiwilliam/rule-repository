"use client";

import { useParams } from "next/navigation";

export default function CreativeReviewPage() {
  const params = useParams();
  const creativeId = params.id as string;

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Creative Review</h1>
        <p className="text-gray-500 mt-1">Creative ID: {creativeId}</p>
      </div>
      <div className="bg-white p-8 rounded-lg border text-center">
        <p className="text-gray-500">
          Creative content evaluation coming in Phase 10.
        </p>
        <p className="text-sm text-gray-400 mt-2">
          Will support multi-modal review for advertising claims, brand guidelines, and regulatory compliance.
        </p>
      </div>
    </div>
  );
}
