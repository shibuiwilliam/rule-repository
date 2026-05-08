"use client";

import { useParams } from "next/navigation";

export default function TransactionReviewPage() {
  const params = useParams();
  const transactionId = params.id as string;

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Transaction Review</h1>
        <p className="text-gray-500 mt-1">Transaction ID: {transactionId}</p>
      </div>
      <div className="bg-white p-8 rounded-lg border text-center">
        <p className="text-gray-500">
          Transaction evaluation coming in Phase 10.
        </p>
        <p className="text-sm text-gray-400 mt-2">
          Will support segregation of duties, approval limits, anti-fraud, and tax compliance checks.
        </p>
      </div>
    </div>
  );
}
