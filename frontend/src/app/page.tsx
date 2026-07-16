"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/error-state";
import { StatTile } from "@/components/stat-tile";
import { RankedBarChart } from "@/components/ranked-bar-chart";
import { useAsync } from "@/hooks/use-async";
import { api } from "@/lib/api";

export default function DashboardPage() {
  const { data, error, loading, reload } = useAsync(() => api.getDashboard(), []);

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Your opening performance at a glance, aggregated across every game you&apos;ve uploaded.
        </p>
      </div>

      {error && <ErrorState message={error} onRetry={reload} />}

      {!error && loading && (
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-24" />
          ))}
        </div>
      )}

      {!error && !loading && data && (
        <>
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <StatTile label="Games analyzed" value={String(data.games_analyzed)} />
            <StatTile label="Opening score" value={`${data.opening_score}/100`} hint="Higher is better" />
            <StatTile
              label="Avg. move leaving theory"
              value={data.avg_move_leaving_theory ? `#${data.avg_move_leaving_theory}` : "—"}
            />
            <StatTile label="Recurring mistake types" value={String(data.most_common_mistakes.length)} />
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Most played openings</CardTitle>
              </CardHeader>
              <CardContent>
                {data.most_played_openings.length === 0 ? (
                  <EmptyChart />
                ) : (
                  <RankedBarChart
                    data={data.most_played_openings.map((o) => ({ name: o.opening_name, value: o.count }))}
                  />
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Weakest openings</CardTitle>
                <p className="text-xs text-muted-foreground">By average evaluation lost per game (pawns)</p>
              </CardHeader>
              <CardContent>
                {data.weakest_openings.length === 0 ? (
                  <EmptyChart />
                ) : (
                  <RankedBarChart
                    data={data.weakest_openings.map((o) => ({ name: o.opening_name, value: Math.abs(o.avg_eval_loss) }))}
                    valueFormatter={(v) => `-${v.toFixed(2)}`}
                  />
                )}
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Most common mistakes</CardTitle>
            </CardHeader>
            <CardContent>
              {data.most_common_mistakes.length === 0 ? (
                <EmptyChart />
              ) : (
                <RankedBarChart
                  data={data.most_common_mistakes.map((m) => ({
                    name: m.mistake_type.replaceAll("_", " "),
                    value: m.occurrences,
                  }))}
                />
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}

function EmptyChart() {
  return (
    <p className="py-10 text-center text-sm text-muted-foreground">
      No games analyzed yet. Head to the Upload page to get started.
    </p>
  );
}
