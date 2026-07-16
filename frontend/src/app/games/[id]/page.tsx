"use client";

import * as React from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/error-state";
import { useAsync } from "@/hooks/use-async";
import { api } from "@/lib/api";

export default function GameDetailPage() {
  const params = useParams<{ id: string }>();
  const gameId = Number(params.id);

  const { data, error, loading, reload } = useAsync(() => api.getGame(gameId), [gameId]);

  return (
    <div className="flex flex-col gap-6">
      <Link href="/games" className="flex w-fit items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="h-4 w-4" /> Back to games
      </Link>

      {error && <ErrorState message={error} onRetry={reload} />}

      {!error && loading && (
        <div className="flex flex-col gap-3">
          <Skeleton className="h-8 w-64" />
          <Skeleton className="h-40 w-full" />
        </div>
      )}

      {!error && !loading && data && (
        <>
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">
              {data.white} vs {data.black}
            </h1>
            <div className="mt-2 flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
              <Badge variant="outline">{data.result}</Badge>
              {data.opening_name && <span>{data.opening_name}</span>}
              {data.eco_code && <span>· {data.eco_code}</span>}
              {data.game_date && <span>· {data.game_date}</span>}
            </div>
          </div>

          <div className="grid gap-6 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Theory exit</CardTitle>
              </CardHeader>
              <CardContent>
                {data.theory_exit ? (
                  <dl className="grid grid-cols-2 gap-y-2 text-sm">
                    <dt className="text-muted-foreground">Left theory at move</dt>
                    <dd>{data.theory_exit.exit_move_number}</dd>
                    <dt className="text-muted-foreground">Played</dt>
                    <dd className="font-mono">{data.theory_exit.played_move_san}</dd>
                    <dt className="text-muted-foreground">Book suggests</dt>
                    <dd className="font-mono">{data.theory_exit.expected_move_san ?? "—"}</dd>
                  </dl>
                ) : (
                  <p className="text-sm text-muted-foreground">
                    No clear theory-exit point found (either the whole game stayed within known theory, or the
                    reference line ran out of recorded depth).
                  </p>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">Mistakes detected</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-3xl font-semibold">{data.mistake_count}</p>
                <p className="text-sm text-muted-foreground">
                  See the <Link href="/mistakes" className="underline">Mistakes</Link> page for grouped detail and
                  coaching explanations.
                </p>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Move list</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-x-6 gap-y-1 font-mono text-sm sm:grid-cols-3 md:grid-cols-4">
                {data.moves
                  .filter((m) => m.color === "white")
                  .map((whiteMove, i) => {
                    const blackMove = data.moves.find((m) => m.move_number === whiteMove.move_number && m.color === "black");
                    return (
                      <div key={i} className="flex gap-2">
                        <span className="w-6 text-muted-foreground">{whiteMove.move_number}.</span>
                        <span className={whiteMove.is_book_move ? "" : "text-accent-foreground"}>{whiteMove.san}</span>
                        {blackMove && <span className={blackMove.is_book_move ? "" : "text-accent-foreground"}>{blackMove.san}</span>}
                      </div>
                    );
                  })}
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
