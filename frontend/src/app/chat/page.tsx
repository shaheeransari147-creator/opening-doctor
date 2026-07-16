"use client";

import * as React from "react";
import { Send, Bot, User } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { ErrorState } from "@/components/error-state";
import { api, ApiError, Citation } from "@/lib/api";
import { cn } from "@/lib/utils";

interface ChatEntry {
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
}

const SUGGESTIONS = [
  "Why is h6 bad in the opening?",
  "Explain the Italian Game.",
  "How do I beat the London System?",
  "Show master examples of the Ruy Lopez.",
];

export default function ChatPage() {
  const [messages, setMessages] = React.useState<ChatEntry[]>([]);
  const [question, setQuestion] = React.useState("");
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  async function send(text: string) {
    const trimmed = text.trim();
    if (!trimmed || loading) return;

    setMessages((prev) => [...prev, { role: "user", content: trimmed }]);
    setQuestion("");
    setLoading(true);
    setError(null);

    try {
      const response = await api.chat(trimmed);
      setMessages((prev) => [...prev, { role: "assistant", content: response.answer_markdown, citations: response.citations }]);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Couldn't reach the chat service. Make sure the backend and an LLM provider are running."
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex h-[calc(100vh-8rem)] flex-col gap-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Ask Opening Doctor</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Answers are grounded in the opening knowledge base only, with sources cited — never freeform chat.
        </p>
      </div>

      <div className="flex-1 overflow-y-auto rounded-xl border bg-card p-4">
        {messages.length === 0 && (
          <div className="flex h-full flex-col items-center justify-center gap-4 text-center">
            <Bot className="h-8 w-8 text-muted-foreground" />
            <p className="text-sm text-muted-foreground">Ask a question about openings, plans, or mistakes.</p>
            <div className="flex flex-wrap justify-center gap-2">
              {SUGGESTIONS.map((s) => (
                <Button key={s} variant="outline" size="sm" onClick={() => send(s)}>
                  {s}
                </Button>
              ))}
            </div>
          </div>
        )}

        <div className="flex flex-col gap-4">
          {messages.map((m, i) => (
            <div key={i} className={cn("flex gap-3", m.role === "user" && "justify-end")}>
              {m.role === "assistant" && (
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
                  <Bot className="h-4 w-4" />
                </div>
              )}
              <div
                className={cn(
                  "max-w-[80%] rounded-lg px-4 py-2.5 text-sm whitespace-pre-wrap",
                  m.role === "user" ? "bg-primary text-primary-foreground" : "bg-secondary text-secondary-foreground"
                )}
              >
                {m.content}
                {m.citations && m.citations.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {m.citations.map((c, ci) => (
                      <Badge key={ci} variant="outline" className="font-normal">
                        [{ci + 1}] {c.opening}
                      </Badge>
                    ))}
                  </div>
                )}
              </div>
              {m.role === "user" && (
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-secondary">
                  <User className="h-4 w-4" />
                </div>
              )}
            </div>
          ))}
          {loading && <p className="text-sm text-muted-foreground">Thinking…</p>}
        </div>
      </div>

      {error && <ErrorState message={error} />}

      <form
        onSubmit={(e) => {
          e.preventDefault();
          send(question);
        }}
        className="flex gap-2"
      >
        <Textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              send(question);
            }
          }}
          placeholder="Ask about an opening, a move, or a mistake…"
          className="min-h-11 resize-none"
        />
        <Button type="submit" disabled={loading || !question.trim()} size="icon">
          <Send className="h-4 w-4" />
        </Button>
      </form>
    </div>
  );
}
