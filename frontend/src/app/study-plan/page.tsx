"use client";

import { Clock } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/error-state";
import { useAsync } from "@/hooks/use-async";
import { api, StudyPlanItem } from "@/lib/api";

const PRIORITY_VARIANT = { high: "destructive", medium: "warning", low: "secondary" } as const;

export default function StudyPlanPage() {
  const { data, error, loading, reload } = useAsync(() => api.getStudyPlan(), []);

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Today&apos;s study plan</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Prioritized from your weakest openings and most common recurring mistakes.
        </p>
      </div>

      {error && <ErrorState message={error} onRetry={reload} />}

      {!error && loading && (
        <div className="flex flex-col gap-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-20 w-full" />
          ))}
        </div>
      )}

      {!error && !loading && data && (
        <>
          {data.items.length === 0 ? (
            <p className="py-10 text-center text-sm text-muted-foreground">
              Not enough data yet to build a study plan. Upload some games first.
            </p>
          ) : (
            <>
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Clock className="h-4 w-4" /> {data.total_minutes} minutes total
              </div>
              <div className="flex flex-col gap-3">
                {data.items.map((item, i) => (
                  <StudyPlanRow key={i} item={item} />
                ))}
              </div>
            </>
          )}
        </>
      )}
    </div>
  );
}

function StudyPlanRow({ item }: { item: StudyPlanItem }) {
  return (
    <Card>
      <CardContent className="flex items-center justify-between gap-4 pt-6">
        <div className="min-w-0">
          <p className="font-medium">{item.activity}</p>
          <p className="mt-1 text-sm text-muted-foreground">{item.reason}</p>
        </div>
        <div className="flex shrink-0 flex-col items-end gap-1.5">
          <Badge variant={PRIORITY_VARIANT[item.priority as keyof typeof PRIORITY_VARIANT] ?? "secondary"}>
            {item.priority}
          </Badge>
          <span className="text-sm text-muted-foreground">{item.minutes} min</span>
        </div>
      </CardContent>
    </Card>
  );
}
