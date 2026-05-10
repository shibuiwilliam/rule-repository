"use client";

import { useState, useRef, useEffect } from "react";

interface Citation {
  rule_id: string;
  statement: string;
  relevance_score: number;
}

interface Message {
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
}

export default function AssistantPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMessage = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: userMessage }]);
    setLoading(true);

    try {
      const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
      const resp = await fetch(`${apiBase}/api/v1/assistant/turn`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_message: userMessage,
          language: "ja",
        }),
      });

      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status}`);
      }

      const data = await resp.json();
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: data.answer,
          citations: data.citations,
        },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "An error occurred. Please try again.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto flex h-[calc(100vh-8rem)] max-w-3xl flex-col">
      <h1 className="mb-4 text-2xl font-bold">Rule Assistant</h1>
      <p className="mb-4 text-sm text-gray-500">
        Ask compliance questions in natural language. The assistant searches
        applicable rules and provides answers with citations.
      </p>

      <div className="flex-1 overflow-y-auto rounded-lg border bg-gray-50 p-4">
        {messages.length === 0 && (
          <div className="flex h-full items-center justify-center text-gray-400">
            <p>Ask a question about rules, policies, or compliance...</p>
          </div>
        )}
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`mb-4 ${msg.role === "user" ? "text-right" : "text-left"}`}
          >
            <div
              className={`inline-block max-w-[80%] rounded-lg px-4 py-2 ${
                msg.role === "user"
                  ? "bg-blue-600 text-white"
                  : "bg-white text-gray-800 shadow-sm"
              }`}
            >
              <p className="whitespace-pre-wrap">{msg.content}</p>
              {msg.citations && msg.citations.length > 0 && (
                <div className="mt-2 border-t pt-2">
                  <p className="text-xs font-semibold text-gray-500">Citations:</p>
                  {msg.citations.map((c, j) => (
                    <p key={j} className="text-xs text-gray-500">
                      [{c.rule_id}] {c.statement.slice(0, 80)}...
                    </p>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="mb-4 text-left">
            <div className="inline-block rounded-lg bg-white px-4 py-2 shadow-sm">
              <p className="text-gray-400">Thinking...</p>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="mt-4 flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSend()}
          placeholder="Ask about a rule, policy, or compliance question..."
          className="flex-1 rounded-lg border px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
          disabled={loading}
        />
        <button
          onClick={handleSend}
          disabled={loading || !input.trim()}
          className="rounded-lg bg-blue-600 px-6 py-2 text-white hover:bg-blue-700 disabled:opacity-50"
        >
          Send
        </button>
      </div>
    </div>
  );
}
