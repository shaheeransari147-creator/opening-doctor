# Restarting Opening Doctor locally (no Docker)

If the terminal sessions running the app get closed, bring everything back
up with these steps, in order.

## 1. Start Postgres (if not already running)

```powershell
& "C:\pgsql17\bin\pg_ctl.exe" -D "C:\pgsql17\data" -l "C:\pgsql17\logfile.txt" start
```

## 2. Start Ollama (if not already running)

Ollama installs as a background service and usually starts automatically on
login. Check with:

```powershell
ollama list
```

If that fails to connect, start it manually:

```powershell
ollama serve
```

## 3. Start the backend

```powershell
cd C:\Users\Lenovo\Downloads\public_html
.\backend\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Runs at http://localhost:8000 (Swagger docs at `/docs`).

## 4. Start the frontend

In a second terminal:

```powershell
cd C:\Users\Lenovo\Downloads\public_html\frontend
npm run dev
```

Runs at http://localhost:3000.

## Verify everything is up

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-WebRequest http://localhost:3000 -UseBasicParsing | Select-Object StatusCode
```

Both should respond without error. If the dashboard shows no data, the demo
seed data may not have been loaded yet — see [SETUP.md](SETUP.md) step 1
(`python -m database.seed.load_opening_book`, `index_knowledge_base`,
`seed_games`).
