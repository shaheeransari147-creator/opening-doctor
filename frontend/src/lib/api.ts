const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { ...(init?.body instanceof FormData ? {} : { "Content-Type": "application/json" }), ...init?.headers },
    cache: "no-store",
  });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      // response had no JSON body
    }
    throw new ApiError(res.status, detail);
  }

  return res.json() as Promise<T>;
}

// ---------- Types (mirroring backend/app/schemas/*.py) ----------

export interface GameSummary {
  id: number;
  white: string;
  black: string;
  result: string;
  event: string | null;
  game_date: string | null;
  opening_name: string | null;
  eco_code: string | null;
  opening_variation: string | null;
  theory_exit_move: number | null;
}

export interface MoveOut {
  ply: number;
  move_number: number;
  color: string;
  san: string;
  fen_after: string;
  is_book_move: boolean;
}

export interface TheoryExitOut {
  exit_move_number: number;
  color_to_move: string;
  expected_move_san: string | null;
  played_move_san: string | null;
  opening_name: string | null;
  eco_code: string | null;
}

export interface GameDetail extends GameSummary {
  moves: MoveOut[];
  theory_exit: TheoryExitOut | null;
  mistake_count: number;
}

export interface GameListResponse {
  games: GameSummary[];
  total: number;
  limit: number;
  offset: number;
}

export interface UploadResponse {
  games_added: number;
  game_ids: number[];
  mistakes_found: number;
  parse_warnings: string[];
}

export interface Citation {
  opening: string;
  theme: string;
  source: string;
}

export interface MistakeGameRef {
  game_id: number;
  opponent: string;
  game_date: string | null;
  move_number: number;
  color: string;
  result: string;
}

export interface MistakeGroup {
  mistake_type: string;
  san: string;
  occurrences: number;
  avg_eval_loss: number;
  example_description: string;
  games: MistakeGameRef[];
  headline: string;
  explanation: { explanation_markdown: string; citations: Citation[] } | null;
}

export interface MistakeListResponse {
  groups: MistakeGroup[];
  limit: number;
  offset: number;
}

export interface DashboardResponse {
  games_analyzed: number;
  opening_score: number;
  most_played_openings: { opening_name: string; count: number }[];
  weakest_openings: { opening_name: string; games_played: number; mistake_count: number; avg_eval_loss: number }[];
  avg_move_leaving_theory: number | null;
  most_common_mistakes: { mistake_type: string; occurrences: number; avg_eval_loss: number }[];
}

export interface OpeningStats {
  opening_name: string;
  eco: string | null;
  games_played: number;
  wins: number;
  draws: number;
  losses: number;
  avg_theory_exit_move: number | null;
  mistake_count: number;
}

export interface OpeningListResponse {
  openings: OpeningStats[];
  total: number;
  limit: number;
  offset: number;
}

export interface StudyPlanItem {
  activity: string;
  minutes: number;
  priority: string;
  reason: string;
}

export interface StudyPlanResponse {
  items: StudyPlanItem[];
  total_minutes: number;
}

export interface ChatResponse {
  answer_markdown: string;
  citations: Citation[];
}

// ---------- API functions ----------

export const api = {
  uploadPgn: (params: { pgnText?: string; file?: File; playerName?: string }) => {
    const form = new FormData();
    if (params.file) form.append("file", params.file);
    if (params.pgnText) form.append("pgn_text", params.pgnText);
    if (params.playerName) form.append("player_name", params.playerName);
    return request<UploadResponse>("/api/upload", { method: "POST", body: form });
  },

  analyze: (gameId?: number) =>
    request<{ games_analyzed: number; game_ids: number[]; mistakes_found: number }>("/api/analyze", {
      method: "POST",
      body: JSON.stringify({ game_id: gameId ?? null }),
    }),

  listGames: (params: { search?: string; limit?: number; offset?: number } = {}) => {
    const qs = new URLSearchParams();
    if (params.search) qs.set("search", params.search);
    qs.set("limit", String(params.limit ?? 20));
    qs.set("offset", String(params.offset ?? 0));
    return request<GameListResponse>(`/api/games?${qs}`);
  },

  getGame: (id: number) => request<GameDetail>(`/api/games/${id}`),

  listMistakes: (params: { explain?: boolean; limit?: number; offset?: number } = {}) => {
    const qs = new URLSearchParams();
    if (params.explain) qs.set("explain", "true");
    qs.set("limit", String(params.limit ?? 20));
    qs.set("offset", String(params.offset ?? 0));
    return request<MistakeListResponse>(`/api/mistakes?${qs}`);
  },

  getDashboard: () => request<DashboardResponse>("/api/dashboard"),

  listOpenings: (params: { search?: string; limit?: number; offset?: number } = {}) => {
    const qs = new URLSearchParams();
    if (params.search) qs.set("search", params.search);
    qs.set("limit", String(params.limit ?? 20));
    qs.set("offset", String(params.offset ?? 0));
    return request<OpeningListResponse>(`/api/openings?${qs}`);
  },

  getStudyPlan: () => request<StudyPlanResponse>("/api/study-plan"),

  chat: (question: string) =>
    request<ChatResponse>("/api/chat", { method: "POST", body: JSON.stringify({ question }) }),
};
