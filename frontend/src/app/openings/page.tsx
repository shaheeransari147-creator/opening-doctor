"use client";

import * as React from "react";
import { Search } from "lucide-react";

import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/error-state";
import { useAsync } from "@/hooks/use-async";
import { api } from "@/lib/api";

const PAGE_SIZE = 10;

export default function OpeningsPage() {
  const [search, setSearch] = React.useState("");
  const [offset, setOffset] = React.useState(0);

  const { data, error, loading, reload } = useAsync(
    () => api.listOpenings({ search: search || undefined, limit: PAGE_SIZE, offset }),
    [search, offset]
  );

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Openings</h1>
        <p className="mt-1 text-sm text-muted-foreground">Per-opening stats aggregated from your analyzed games.</p>
      </div>

      <div className="relative max-w-sm">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          value={search}
          onChange={(e) => {
            setOffset(0);
            setSearch(e.target.value);
          }}
          placeholder="Search openings…"
          className="pl-9"
        />
      </div>

      {error && <ErrorState message={error} onRetry={reload} />}

      {!error && loading && (
        <div className="flex flex-col gap-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-14 w-full" />
          ))}
        </div>
      )}

      {!error && !loading && data && (
        <>
          {data.openings.length === 0 ? (
            <p className="py-10 text-center text-sm text-muted-foreground">No openings found yet.</p>
          ) : (
            <div className="overflow-x-auto rounded-xl border">
              <table className="w-full text-sm">
                <thead className="bg-secondary/60 text-left text-xs text-muted-foreground">
                  <tr>
                    <th className="px-4 py-2 font-medium">Opening</th>
                    <th className="px-4 py-2 font-medium">ECO</th>
                    <th className="px-4 py-2 font-medium">Games</th>
                    <th className="px-4 py-2 font-medium">W / D / L</th>
                    <th className="px-4 py-2 font-medium">Avg. move leaving theory</th>
                    <th className="px-4 py-2 font-medium">Mistakes</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {data.openings.map((o) => (
                    <tr key={o.opening_name} className="bg-card">
                      <td className="px-4 py-2.5 font-medium">{o.opening_name}</td>
                      <td className="px-4 py-2.5 text-muted-foreground">{o.eco ?? "—"}</td>
                      <td className="px-4 py-2.5">{o.games_played}</td>
                      <td className="px-4 py-2.5 tabular-nums">
                        {o.wins} / {o.draws} / {o.losses}
                      </td>
                      <td className="px-4 py-2.5">{o.avg_theory_exit_move ?? "—"}</td>
                      <td className="px-4 py-2.5">{o.mistake_count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <div className="flex items-center justify-between">
            <p className="text-xs text-muted-foreground">
              {data.total === 0 ? "0 results" : `${offset + 1}-${Math.min(offset + PAGE_SIZE, data.total)} of ${data.total}`}
            </p>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}>
                Previous
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={offset + PAGE_SIZE >= data.total}
                onClick={() => setOffset(offset + PAGE_SIZE)}
              >
                Next
              </Button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
