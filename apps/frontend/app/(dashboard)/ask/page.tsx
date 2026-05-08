"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import Link from "next/link";

interface Citation {
  rule_id: string;
  statement: string;
  source_refs: Array<Record<string, unknown>>;
  relevance_score: number;
}

interface AskResponse {
  answer: string;
  citations: Citation[];
  intent: string;
  can_register_proposal: boolean;
}

interface Message {
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  canPropose?: boolean;
}

export default function AskPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content:
        "Welcome to the Rule Assistant! Ask me any question about your organization's rules and policies. I'll find relevant rules and provide cited answers.",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleSend = useCallback(async () => {
    if (!input.trim() || loading) return;

    const question = input.trim();
    const userMessage: Message = { role: "user", content: question };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);

    try {
      const API_BASE =
        process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
      const res = await fetch(`${API_BASE}/api/v1/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });

      if (!res.ok) {
        throw new Error(`API error ${res.status}`);
      }

      const data: AskResponse = await res.json();

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: data.answer,
          citations: data.citations,
          canPropose: data.can_register_proposal,
        },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content:
            "Sorry, I encountered an error processing your question. Please try again.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  }, [input, loading]);

  return (
    <div className="flex h-[calc(100vh-8rem)] flex-col">
      {/* Header */}
      <div className="mb-4">
        <h1 className="text-2xl font-bold">Rule Assistant</h1>
        <p className="text-sm text-gray-500">
          Ask questions about rules across all departments. Get cited answers
          with links to source rules.
        </p>
      </div>

      {/* Message area */}
      <div className="flex-1 overflow-y-auto rounded-lg border bg-white p-4">
        <div className="space-y-4">
          {messages.map((msg, i) => (
            <div
              key={i}
              className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[75%] rounded-lg px-4 py-3 text-sm ${
                  msg.role === "user"
                    ? "bg-blue-600 text-white"
                    : "bg-gray-100 text-gray-800"
                }`}
              >
                <p className="whitespace-pre-wrap">{msg.content}</p>

                {/* Citations */}
                {msg.citations && msg.citations.length > 0 && (
                  <div className="mt-3 space-y-2 border-t border-gray-200 pt-2">
                    <p className="text-xs font-medium text-gray-500">
                      Referenced rules:
                    </p>
                    {msg.citations.map((citation) => (
                      <Link
                        key={citation.rule_id}
                        href={`/rules/${citation.rule_id}`}
                        className="block rounded border border-gray-200 bg-white p-2 text-xs text-gray-700 hover:border-blue-300 hover:bg-blue-50"
                      >
                        <span className="font-medium text-blue-600">
                          {citation.rule_id.slice(0, 8)}...
                        </span>
                        <span className="ml-2">
                          {citation.statement.length > 120
                            ? `${citation.statement.slice(0, 120)}...`
                            : citation.statement}
                        </span>
                        {citation.relevance_score > 0 && (
                          <span className="ml-2 rounded bg-gray-100 px-1.5 py-0.5 text-xs text-gray-500">
                            {Math.round(citation.relevance_score * 100)}%
                          </span>
                        )}
                      </Link>
                    ))}
                  </div>
                )}

                {/* Proposal suggestion */}
                {msg.canPropose &&
                  msg.citations &&
                  msg.citations.length === 0 && (
                    <div className="mt-2 border-t border-gray-200 pt-2">
                      <Link
                        href="/proposals"
                        className="text-xs text-blue-600 hover:underline"
                      >
                        Create a rule proposal for this topic
                      </Link>
                    </div>
                  )}
              </div>
            </div>
          ))}
          {loading && (
            <div className="flex justify-start">
              <div className="rounded-lg bg-gray-100 px-4 py-2 text-sm text-gray-500">
                Searching rules...
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input area */}
      <div className="mt-4 flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              handleSend();
            }
          }}
          placeholder="Ask about rules, policies, or compliance..."
          className="flex-1 rounded-lg border px-4 py-2 text-sm focus:border-blue-500 focus:outline-none"
          disabled={loading}
        />
        <button
          onClick={handleSend}
          disabled={loading || !input.trim()}
          className="rounded-lg bg-blue-600 px-6 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-40"
        >
          Ask
        </button>
      </div>
    </div>
  );
}
