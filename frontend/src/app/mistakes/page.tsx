"use client";

import * as React from "react";
import { Sparkles } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/error-state";
import { useAsync } from "@/hooks/use-async";
import { api, MistakeGroup } from "@/lib/api";

export default function MistakesPage() {
  const { data, error, loading, reload } = useAsync(() => api.listMistakes({ limit: 20 }), []);

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Recurring mistakes</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Mistakes grouped across all your games. Click &quot;Explain&quot; on any group for an AI coaching
          breakdown grounded in the opening knowledge base.
        </p>
      </div>

      {error && <ErrorState message={error} onRetry={reload} />}

      {!error && loading && (
        <div className="flex flex-col gap-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-24 w-full" />
          ))}
        </div>
      )}

      {!error && !loading && data && (
        <>
          {data.groups.length === 0 ? (
            <p className="py-10 text-center text-sm text-muted-foreground">
              No mistakes detected yet. Upload some games to get started.
            </p>
          ) : (
            <div className="flex flex-col gap-4">
              {data.groups.map((group) => (
                <MistakeCard key={`${group.mistake_type}-${group.san}`} group={group} />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}

function MistakeCard({ group }: { group: MistakeGroup }) {
  const [explanation, setExplanation] = React.useState(group.explanation);
  const [loadingExplain, setLoadingExplain] = React.useState(false);
  const [explainError, setExplainError] = React.useState<string | null>(null);

  async function handleExplain() {
    setLoadingExplain(true);
    setExplainError(null);
    try {
      const response = await api.listMistakes({ explain: true, limit: 1, offset: 0 });
      const match = response.groups.find((g) => g.mistake_type === group.mistake_type && g.san === group.san);
      setExplanation(match?.explanation ?? null);
    } catch {
      setExplainError(
        "Couldn't generate an explanation. Make sure an LLM provider is configured (see .env / README)."
      );
    } finally {
      setLoadingExplain(false);
    }
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between space-y-0">
        <div>
          <CardTitle className="text-base">{group.headline}</CardTitle>
          <p className="mt-1 text-sm text-muted-foreground">{group.example_description}</p>
        </div>
        <Badge variant="warning">{group.avg_eval_loss.toFixed(2)} avg. eval loss</Badge>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        {!explanation && (
          <Button variant="outline" size="sm" className="w-fit" onClick={handleExplain} disabled={loadingExplain}>
            <Sparkles className="h-4 w-4" />
            {loadingExplain ? "Thinking…" : "Explain like a coach"}
          </Button>
        )}

        {explainError && <ErrorState message={explainError} />}

        {explanation && (
          <div className="rounded-lg border bg-secondary/40 p-4 text-sm leading-relaxed whitespace-pre-wrap">
            {explanation.explanation_markdown}
            <div className="mt-3 flex flex-wrap gap-1.5">
              {explanation.citations.map((c, i) => (
                <Badge key={i} variant="secondary" className="font-normal">
                  [{i + 1}] {c.opening} · {c.theme.replaceAll("_", " ")}
                </Badge>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
