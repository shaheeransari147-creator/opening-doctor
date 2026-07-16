"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { UploadCloud, FileText, CheckCircle2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { ErrorState } from "@/components/error-state";
import { api, ApiError, UploadResponse } from "@/lib/api";

export default function UploadPage() {
  const router = useRouter();
  const [pgnText, setPgnText] = React.useState("");
  const [file, setFile] = React.useState<File | null>(null);
  const [playerName, setPlayerName] = React.useState("");
  const [submitting, setSubmitting] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [result, setResult] = React.useState<UploadResponse | null>(null);

  const canSubmit = (pgnText.trim().length > 0 || file) && !submitting;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!canSubmit) return;

    setSubmitting(true);
    setError(null);
    setResult(null);

    try {
      const response = await api.uploadPgn({ pgnText: pgnText.trim() || undefined, file: file ?? undefined, playerName: playerName.trim() || undefined });
      setResult(response);
      setPgnText("");
      setFile(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Upload failed. Please check your PGN and try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Upload games</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Upload a .pgn file or paste PGN text below. Every game is immediately analyzed for opening,
          theory-exit point, and recurring opening mistakes.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="flex flex-col gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Your name (optional)</CardTitle>
            <CardDescription>
              If given, only this player&apos;s moves are analyzed for mistakes (matched against White/Black).
              Otherwise, both sides are analyzed.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Input
              value={playerName}
              onChange={(e) => setPlayerName(e.target.value)}
              placeholder="e.g. your username as it appears in the PGN"
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <FileText className="h-4 w-4" /> Paste PGN text
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Textarea
              value={pgnText}
              onChange={(e) => setPgnText(e.target.value)}
              placeholder={'[Event "Casual Game"]\n[White "Alice"]\n[Black "Bob"]\n[Result "1-0"]\n\n1. e4 e5 2. Nf3 Nc6 ...'}
              className="min-h-48 font-mono text-xs"
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <UploadCloud className="h-4 w-4" /> Or upload a .pgn file
            </CardTitle>
          </CardHeader>
          <CardContent>
            <input
              type="file"
              accept=".pgn,.txt"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              className="block w-full text-sm text-muted-foreground file:mr-4 file:rounded-md file:border-0 file:bg-secondary file:px-4 file:py-2 file:text-sm file:font-medium file:text-secondary-foreground hover:file:bg-secondary/80"
            />
            {file && <p className="mt-2 text-xs text-muted-foreground">Selected: {file.name}</p>}
          </CardContent>
        </Card>

        {error && <ErrorState message={error} />}

        {result && (
          <Card className="border-primary/40 bg-primary/5">
            <CardContent className="flex flex-col gap-3 pt-6">
              <div className="flex items-center gap-2 text-primary">
                <CheckCircle2 className="h-5 w-5" />
                <p className="font-medium">
                  Analyzed {result.games_added} game{result.games_added !== 1 ? "s" : ""}, found{" "}
                  {result.mistakes_found} mistake{result.mistakes_found !== 1 ? "s" : ""}.
                </p>
              </div>
              <div className="flex gap-2">
                <Button size="sm" variant="outline" onClick={() => router.push("/")} type="button">
                  View dashboard
                </Button>
                <Button size="sm" variant="outline" onClick={() => router.push("/mistakes")} type="button">
                  View mistakes
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        <Button type="submit" disabled={!canSubmit} className="self-start">
          {submitting ? "Analyzing…" : "Upload & analyze"}
        </Button>
      </form>
    </div>
  );
}
