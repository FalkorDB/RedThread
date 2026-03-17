# 🔴 RedThread — Graph-Powered Financial Investigation Platform

**Discover hidden connections. Trace money flows. Map fraud networks.**

RedThread is an open-source investigation intelligence platform that uses graph database technology to help analysts uncover relationships that would be invisible in spreadsheets and traditional databases. Built on [FalkorDB](https://www.falkordb.com/) for lightning-fast graph traversals.

Think of it as the **detective's evidence board** — digitized, automated, and powered by graph algorithms that can find connections across 6+ hops in milliseconds.

---

## Why Graph?

**Before (spreadsheets & SQL):** An analyst manually cross-references 15 spreadsheets to find that Company A is owned by Trust B, which is directed by the same nominee who also controls Company C, which received funds that eventually reached the suspect's personal account. This takes **days or weeks**.

**After (RedThread):** Click "Find Hidden Connections" → instant visualization of a 4-hop money laundering chain through 3 shell companies across 5 jurisdictions. **Seconds, not weeks.**

The core insight: financial crime networks are **graphs** — people connected to organizations connected to accounts connected through transactions. Relational databases struggle with variable-depth traversals, cycle detection, and path finding. Graph databases make these operations native and fast.

---

## Features

### 🔗 Path Finding
Discover all connections between any two entities, from direct relationships to hidden 6-hop chains through intermediaries.

### 💰 Money Flow Tracing  
Follow the money through directed account-to-account transfers with amount aggregation — trace how funds flow and split across the network.

### 🔄 Circular Flow Detection
Automatically detect circular transaction patterns (A→B→C→A) — a classic money laundering indicator that's nearly impossible to spot in flat data.

### 🏢 Shell Company Chain Detection
Identify cross-jurisdiction corporate chains: Person → Company (BVI) → Trust (Cayman) → Subsidiary (Panama) — with automatic jurisdiction risk scoring.

### 💰 Structuring Detection
Find "smurfing" patterns — multiple transactions just below reporting thresholds — by analyzing transaction amounts across accounts.

### ⚠️ Risk Score Computation
Compute entity risk scores through network propagation: high-risk jurisdictions, connected suspicious entities, and transaction patterns all contribute, with risk diminishing by graph distance.

### 📊 Network Analytics
Degree centrality (most connected entities), bridge detection (entities connecting otherwise isolated groups), shared connections, and entity timelines.

### 🔍 Interactive Graph Visualization
Explore the network visually — click to expand, double-click to explore neighbors, drag to rearrange. Color-coded by entity type with risk-based sizing.

### 📁 Data Import
Import entities and relationships via CSV or JSON. Column mapping, validation, and entity resolution built in.

### 📋 Case Management
Create investigations, pin entities of interest, save graph snapshots, tag entities, and export reports.

### ⏳ Temporal Graph Analysis
All relationships carry `valid_from` / `valid_to` properties. Use the timeline slider in the UI to view the graph as it existed at any point in time, see what changed between two dates, and explore entity temporal profiles — understand when connections formed and dissolved.

### 📸 Graph Diff / Comparison Views
Take snapshots of the current graph state and compare any two snapshots (or current state vs. a snapshot) to find added/removed nodes and relationships. Ideal for tracking how a network evolves over the course of an investigation.

### 🗣️ Natural Language Query (LLM → Cypher)
Type questions in plain English — e.g. *"show me all money flows from Kovacs to accounts in Panama"* — and the system translates them to Cypher queries via an OpenAI-compatible API. Includes safety checks (read-only queries only) and graceful degradation when no API key is configured.

> **Note:** Natural Language Query requires an OpenAI-compatible API key set via `LLM_API_KEY`. The feature is optional — all other functionality works without it.

---

## Graph Schema

```
[Person] ─DIRECTS──────→ [Organization] ─SUBSIDIARY_OF──→ [Organization]
   │                          │                                │
   ├─EMPLOYED_BY─────────────→│                                │
   │                          │                                │
   ├─OWNS────────────────────→├─OWNS──→[Account]               │
   │                          │           │                    │
   ├─LOCATED_AT──────→[Address]           └─TRANSFERRED_TO──→[Account]
   │                     ↑
   ├─CONTACTED───→[Person]                [Property]
   │                                         ↑
   ├─RELATED_TO──→[Person]                   OWNS
   │
   ├─PARTICIPATED_IN──→[Event]
   │
   └─MENTIONED_IN─────→[Document]
```

**7 node types** · **11 relationship types** · Parameterized Cypher queries throughout

---

## Quick Start

### Option 1: Docker Compose (recommended)

```bash
git clone https://github.com/FalkorDB/RedThread.git
cd RedThread
docker compose up -d
# Demo data is loaded automatically on first launch!
# Open http://localhost:8000
```

> **Tip:** To skip auto-seeding, run `SEED_DATA=false docker compose up -d`. To re-seed, delete the marker: `docker compose exec app rm /app/data/.seeded && docker compose restart app`.

### Option 2: Local Development

```bash
# Start FalkorDB
docker run -d --name falkordb -p 6379:6379 falkordb/falkordb:latest

# Install & run
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m src.seed      # Load demo data
make run                # Start server at http://localhost:8000
```

---

## Demo: Operation Crimson Tide

The seed data contains a realistic financial investigation scenario:

**The Case:** Viktor Kovacs, a former Minister of Infrastructure, is suspected of funneling €23M from government contracts through a network of offshore shell companies. The investigation reveals:

- **15 persons** including politicians, nominees, lawyers, and bankers
- **15 organizations** across 10 jurisdictions (BVI, Cayman Islands, Panama, Seychelles, Belize...)  
- **18 accounts** at banks worldwide
- **25 financial transfers** forming circular flows and structuring patterns
- **117 total relationships** in the network

### Try These Investigations:

1. **Search "Kovacs"** → Click to expand → See his direct connections to shell companies
2. **Click "🔍 Patterns"** → Discover circular money flows and structuring
3. **Select Kovacs → "Find Paths From" → Click an account** → See the money trail
4. **Select Golden Gate Holdings → "⚠️ Risk"** → See risk factors (BVI jurisdiction + high-risk connections)
5. **Double-click any node** → Expand its neighborhood to discover more connections

---

## API Reference

All endpoints return JSON. Interactive docs at `/docs` (Swagger UI).

### Entities
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/entities/?q=search&label=Person` | Search/list entities |
| GET | `/api/entities/{id}` | Get entity details |
| GET | `/api/entities/{id}/neighborhood?depth=2` | Get entity neighborhood |
| GET | `/api/entities/{id}/relationships` | Get entity relationships |
| POST | `/api/entities/person` | Create a person |
| POST | `/api/entities/organization` | Create an organization |
| POST | `/api/entities/account` | Create an account |
| PUT | `/api/entities/{label}/{id}` | Update entity |
| DELETE | `/api/entities/{label}/{id}` | Delete entity |

### Analysis
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/analysis/paths?source=X&target=Y` | Find all paths |
| GET | `/api/analysis/shortest-path?source=X&target=Y` | Shortest path |
| GET | `/api/analysis/money-flow?source=X` | Trace money flow |
| GET | `/api/analysis/reach?entity_id=X&max_depth=3` | Entity reach |
| GET | `/api/analysis/patterns` | Run all pattern detectors |
| GET | `/api/analysis/patterns/circular-flows` | Detect circular transactions |
| GET | `/api/analysis/patterns/shell-companies` | Detect shell company chains |
| GET | `/api/analysis/patterns/structuring` | Detect structuring |
| GET | `/api/analysis/patterns/hidden-connections?entity1=X&entity2=Y` | Hidden connections |
| GET | `/api/analysis/risk/{entity_id}` | Compute risk score |
| GET | `/api/analysis/centrality` | Most connected entities |
| GET | `/api/analysis/timeline/{entity_id}` | Entity activity timeline |
| GET | `/api/analysis/stats` | Graph statistics |

### Investigations
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/api/investigations/` | List/create investigations |
| GET | `/api/investigations/{id}` | Get investigation with entities |
| POST | `/api/investigations/{id}/entities` | Add entity to investigation |
| POST | `/api/investigations/{id}/snapshots` | Save graph snapshot |

### Import/Export
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/import/csv/entities?label=Person` | Import entities from CSV |
| POST | `/api/import/json` | Import entities+relationships from JSON |
| POST | `/api/import/json/inline` | Import from inline JSON body |
| GET | `/api/export/subgraph?entity_id=X` | Export subgraph as JSON |
| GET | `/api/export/report?entity_id=X` | Generate entity report |

### Temporal Analysis
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/temporal/date-range` | Get earliest/latest dates in graph |
| GET | `/api/temporal/graph-at?date=YYYY-MM-DD` | Get graph state at a point in time |
| GET | `/api/temporal/changes?start=X&end=Y` | Get changes between two dates |
| GET | `/api/temporal/timeline` | All dated relationships in chronological order |
| GET | `/api/temporal/entity/{entity_id}` | Entity temporal profile |

### Snapshots & Diff
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/snapshots/?investigation_id=X&name=Y` | Create a snapshot of current graph |
| GET | `/api/snapshots/` | List all snapshots |
| GET | `/api/snapshots/{id}` | Get a specific snapshot |
| GET | `/api/snapshots/diff/compare?snapshot_a=X&snapshot_b=Y` | Diff two snapshots |
| GET | `/api/snapshots/diff/current?snapshot_id=X` | Diff current graph vs a snapshot |

### Natural Language Query
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/nlq/query` | Translate and execute NL query |
| POST | `/api/nlq/translate` | Translate NL to Cypher without executing |
| GET | `/api/nlq/examples` | Get example NL queries |

---

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `FALKORDB_HOST` | `localhost` | FalkorDB host |
| `FALKORDB_PORT` | `6379` | FalkorDB port |
| `FALKORDB_GRAPH_NAME` | `redthread` | Graph name |
| `APP_HOST` | `0.0.0.0` | Application host |
| `APP_PORT` | `8000` | Application port |
| `APP_DEBUG` | `false` | Debug mode |
| `APP_LOG_LEVEL` | `info` | Log level |
| `SQLITE_DB_PATH` | `./data/redthread.db` | SQLite database path |
| `LLM_API_KEY` | `` | OpenAI-compatible API key (optional, for NL query) |
| `LLM_BASE_URL` | `` | Custom LLM endpoint URL (optional) |
| `LLM_MODEL` | `gpt-4o-mini` | LLM model to use for NL→Cypher |

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                         Web Browser                              │
│  ┌──────────┐ ┌──────────┐ ┌────────┐ ┌─────────┐ ┌──────────┐ │
│  │ Graph Viz│ │ Timeline │ │ Search │ │  Tools  │ │ NL Query │ │
│  │(vis-net) │ │  Slider  │ │  Bar   │ │  Panel  │ │   Bar    │ │
│  └────┬─────┘ └────┬─────┘ └───┬────┘ └────┬────┘ └────┬─────┘ │
└───────┼────────────┼───────────┼───────────┼───────────┼────────┘
        │            │           │           │           │
   ┌────▼────────────▼───────────▼───────────▼───────────▼────┐
   │                    FastAPI REST API                        │
   │  /entities  /analysis  /temporal  /snapshots  /nlq        │
   └────┬────────────┬───────────┬───────────┬──────────┬─────┘
        │            │           │           │          │
   ┌────▼────┐  ┌────▼────┐  ┌──▼──────┐ ┌─▼───────┐ ┌▼────────┐
   │ Entity  │  │Analysis │  │Temporal │ │Snapshot │ │  NLQ    │
   │ Service │  │ Service │  │ Service │ │& Diff   │ │ Service │
   └────┬────┘  └────┬────┘  └──┬──────┘ └─┬───────┘ └┬────────┘
        │            │          │           │          │
   ┌────▼────────────▼──────────▼───────────▼──────────▼────┐
   │              Graph Query Layer                          │
   │  queries | pathfinding | patterns | risk | temporal    │
   └──────────────────┬─────────────────────────────────────┘
                      │
           ┌──────────▼──────────┐
           │      FalkorDB       │  ┌──────────┐  ┌──────────┐
           │  (Graph Database)   │  │  SQLite  │  │ LLM API  │
           └─────────────────────┘  │  (Cases) │  │(optional)│
                                    └──────────┘  └──────────┘
```

---

## Development

```bash
make dev          # Install dev dependencies
make lint         # Run linter
make format       # Auto-format code
make test         # Run tests
make test-cov     # Run tests with coverage
make run          # Start dev server with hot reload
make seed         # Load seed data
make docker-up    # Start with Docker Compose
```

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/my-feature`
3. Run tests: `make test`
4. Run linter: `make lint`
5. Commit with conventional commits: `feat(analysis): add community detection`
6. Push and create a PR

---

## License

MIT — see [LICENSE](LICENSE)
