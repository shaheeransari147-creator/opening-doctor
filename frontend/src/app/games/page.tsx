"use client";

import * as React from "react";
import Link from "next/link";
import { Search } from "lucide-react";

import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/error-state";
import { useAsync } from "@/hooks/use-async";
import { api } from "@/lib/api";

const PAGE_SIZE = 10;

function resultVariant(result: string): "success" | "warning" | "destructive" {
  if (result === "1-0") return "success";
  if (result === "1/2-1/2") return "warning";
  return "destructive";
}

export default function GamesPage() {
  const [search, setSearch] = React.useState("");
  const [offset, setOffset] = React.useState(0);

  const { data, error, loading, reload } = useAsync(
    () => api.listGames({ search: search || undefined, limit: PAGE_SIZE, offset }),
    [search, offset]
  );

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Games</h1>
        <p className="mt-1 text-sm text-muted-foreground">Every game you&apos;ve uploaded, with detected opening and theory-exit info.</p>
      </div>

      <div className="relative max-w-sm">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          value={search}
          onChange={(e) => {
            setOffset(0);
            setSearch(e.target.value);
          }}
          placeholder="Search by opening or event…"
          className="pl-9"
        />
      </div>

      {error && <ErrorState message={error} onRetry={reload} />}

      {!error && loading && (
        <div className="flex flex-col gap-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-16 w-full" />
          ))}
        </div>
      )}

      {!error && !loading && data && (
        <>
          {data.games.length === 0 ? (
            <p className="py-10 text-center text-sm text-muted-foreground">
              No games found. Try a different search, or upload some games first.
            </p>
          ) : (
            <div className="flex flex-col divide-y divide-border overflow-hidden rounded-xl border">
              {data.games.map((game) => (
                <Link
                  key={game.id}
                  href={`/games/${game.id}`}
                  className="flex items-center justify-between gap-4 bg-card px-4 py-3 transition-colors hover:bg-secondary/60"
                >
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium">
                      {game.white} vs {game.black}
                    </p>
                    <p className="truncate text-xs text-muted-foreground">
                      {game.opening_name ?? "Unknown opening"}
                      {game.eco_code ? ` · ${game.eco_code}` : ""}
                      {game.theory_exit_move ? ` · left theory at move ${game.theory_exit_move}` : ""}
                    </p>
                  </div>
                  <Badge variant={resultVariant(game.result)}>{game.result}</Badge>
                </Link>
              ))}
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
