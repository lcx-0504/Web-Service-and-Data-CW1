# Presentation Notes — NutriTrack

> 5-minute presentation + 5-minute Q&A. Total: 7 slides.

---

## Slide 1: Title (~10s)

**NutriTrack — Food Nutrition Tracking & Analysis API**

- Chenxi Li
- XJCO3011 Web Services and Web Data — Coursework 1
- April 2026
- Live: https://lichenxi.pythonanywhere.com

---

## Slide 2: Problem & Solution (~50s)

**Problem:**
- People struggle to track daily nutritional intake
- Existing tools are either too complex or not programmable
- AI assistants cannot directly interact with nutrition databases

**Solution: NutriTrack**
- Data-driven REST API built on USDA SR Legacy dataset (7,793 foods, 25 categories)
- Core features:
  - Food search with relevance ranking
  - Meal logging (full CRUD)
  - Nutritional analytics (daily/weekly/balance)
  - Personalised BMR-based recommendations
- MCP integration → AI assistants can use the API through natural language

---

## Slide 3: Tech Stack & Architecture (~50s)

**Tech Stack Table:**

| Component | Choice | Why |
|---|---|---|
| Framework | FastAPI | Lightweight, auto Swagger docs, native Pydantic validation. Better than Django for pure API projects |
| Database | SQLite | Zero-config, portable, sufficient for ~7,800 records |
| ORM | SQLAlchemy 2.0 | Mature, Alembic migrations, complex query support |
| Auth | JWT (python-jose) | Stateless, RESTful-aligned |
| MCP | mcp SDK (FastMCP) | Official Python SDK, stdio transport |

**Architecture Diagram** (use Mermaid screenshot or simplified diagram):

```
HTTP Clients / MCP Server → FastAPI (17 endpoints) → SQLite (7,793 foods + users + meals)
```

---

## Slide 4: Key Features & Design (~60s)

**4 Data Models:**
- User → Meal → MealItem → Food (relationship diagram)

**Smart Search:**
- 3-level relevance ranking: starts-with > word-boundary > substring
- Optional category filter (25 categories)

**Two-Tier Input Validation:**
- Hard reject: impossible values (negative weight, future dates)
- Soft warnings: extreme-but-valid values ("Weight 130 kg is unusually high. Please verify.")

**Personalised Nutrition Analysis:**
- Mifflin-St Jeor equation for BMR calculation
- Adjusts for age, gender, height, weight, activity level
- Balance analysis: low / ok / high status per nutrient

---

## Slide 5: MCP Integration (~40s)

**What is MCP?**
- Model Context Protocol — open standard by Anthropic
- Allows AI assistants to call external tools via structured interface

**Our MCP Server:**
- 16 tools covering all API endpoints
- stdio transport, works with Claude Desktop
- Example: User says "Log a lunch with chicken breast and rice" → AI calls `search_food`, `log_meal` tools

**Show:** Claude Desktop screenshot with 16 tools discovered

---

## Slide 6: Demo (~30s)

**Quick demo (video or live):**
- Play MCP demo video clip (fast-forward through key operations):
  1. AI searches for food → calls `search_food` tool
  2. AI logs a meal → calls `log_meal` tool
  3. AI shows daily summary → calls `get_daily_summary` tool
- Show Swagger UI screenshot with all 17 endpoints

---

## Slide 7: Testing, Deployment & GenAI (~50s)

**Testing:**
- 28 integration tests across 5 modules (Auth, Foods, Meals, Analytics, Profile)
- Supports `--base-url` flag: test local or remote
- All 28 tests passed against PythonAnywhere

**Deployment:**
- PythonAnywhere (free tier)
- Challenge: FastAPI is ASGI, PythonAnywhere only supports WSGI
- Solution: Custom ASGI-to-WSGI bridge using `asyncio.new_event_loop()`

**GenAI Usage:**
- Tools: GitHub Copilot + Claude Code (both Claude Opus 4.6)
- Used for: planning, code generation, debugging, deployment, documentation
- AI excelled at rapid prototyping; human essential for deployment constraints

**Thank you — Questions?**

---

## Q&A Preparation (possible questions)

1. **Why FastAPI over Django?** → Pure API project, auto Swagger, Pydantic validation, lightweight
2. **Why SQLite?** → Coursework scope, zero-config, portable, sufficient for 7,800 records
3. **How does MCP work?** → stdio transport, AI sends tool call → MCP server → HTTP to API → response back
4. **Biggest challenge?** → PythonAnywhere deployment (ASGI/WSGI mismatch, threading disabled)
5. **How did you use GenAI?** → Architecture planning, code generation, debugging, but human review for security and edge cases
6. **Testing approach?** → Integration tests via requests library, configurable base URL, 28 tests covering all modules
7. **How is the search ranked?** → SQL CASE expression: starts-with (rank 0) > word-boundary (rank 1) > substring (rank 2)
8. **What would you improve?** → Micronutrients, frontend UI, PostgreSQL for concurrency, food image recognition
