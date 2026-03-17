# Demo Guide: Operation Crimson Tide

This guide walks you through the most impressive features of RedThread using the pre-loaded investigation scenario.

## Setup

```bash
# Option 1: Docker Compose
docker compose up -d
docker compose exec app python -m src.seed

# Option 2: Local
docker run -d --name falkordb -p 6379:6379 falkordb/falkordb:latest
pip install -r requirements.txt
python -m src.seed
make run
```

Open http://localhost:8000 in your browser.

## The Scenario

Viktor Kovacs, former Hungarian Minister of Infrastructure, is suspected of embezzling €23M from a government highway contract. The money was allegedly laundered through a network of offshore shell companies controlled by nominee directors.

## Investigation Walkthrough

### 1. Discover the Network (2 min)

1. In the **search bar**, type "Kovacs"
2. Click **Viktor Kovacs** — his node appears with direct connections
3. **Double-click** his node to expand neighbors
4. **Double-click** "Golden Gate Holdings" to see its connections
5. Keep expanding — watch the corruption network unfold

### 2. Follow the Money (2 min)

1. In the sidebar, click the **Tools** tab
2. Click on account **GG-001-MAIN** in the sidebar
3. Click **💰 Trace Money Flow** in the detail panel
4. Watch the analysis panel show all downstream money paths
5. Notice the circular flow: Crimson → Sea Breeze → Pacific Rim → Dragon → Golden Gate → Crimson

### 3. Detect Fraud Patterns (1 min)

1. Click **🔍 Patterns** in the top bar
2. Review the results:
   - **Circular Flows**: Money loops through offshore accounts
   - **Shell Company Chains**: Cross-jurisdiction corporate structures
   - **Structuring**: Multiple transfers just below $10,000 threshold
   - **Rapid Pass-Through**: Money transiting through accounts within 24 hours

### 4. Risk Assessment (1 min)

1. Click on **Golden Gate Holdings** in the graph
2. Click **⚠️ Risk** in the detail panel actions
3. See the risk breakdown:
   - BVI jurisdiction: +75 risk
   - Shell company type: +10 risk
   - Connected high-risk entities propagate additional risk

### 5. Find Hidden Connections (1 min)

1. Click **🔗 Path Find** in the top bar
2. Click **Viktor Kovacs** (source)
3. Click **Kenji Yamamoto** (target) — seemingly unrelated
4. Discover they're connected through Golden Gate → Cerulean Trust → Alpine Wealth Management where Yamamoto works

### 6. Explore the Timeline (2 min)

1. Drag the **timeline slider** at the bottom of the graph view to **2010-01-01**
2. Watch the graph show only the relationships that existed at that date — the early seed companies and nominee appointments
3. Slowly slide forward through the years and observe new entities and transfers appearing as the laundering network grows
4. Jump to **2018-06-01** — notice the peak of activity when the majority of funds were being cycled
5. Click on **Viktor Kovacs** and open his **temporal profile** to see a chronological list of all his connections forming and dissolving
6. Use the **"Changes between dates"** feature: set start to **2016-01-01** and end to **2019-01-01** to see exactly which relationships appeared during the core laundering period

### 7. Compare Snapshots (1 min)

1. With the current graph loaded, click **📸 Snapshot** in the toolbar to save the current state
2. Name it "Full Network"
3. Now delete or filter some nodes (e.g., remove all Belize entities)
4. Take another snapshot named "Without Belize"
5. Click **📸 Compare Snapshots** and select both snapshots
6. Review the diff — see exactly which nodes and relationships were removed, highlighted in the comparison view

### 8. Ask Questions in Plain English (1 min)

> **Requires** `LLM_API_KEY` to be configured. Without it, the NL query bar is disabled gracefully.

1. Click the **🗣️ Ask** bar at the top of the interface
2. Type: **"Show me all money flows from Kovacs to accounts in Panama"**
3. The system translates this to a Cypher query, executes it (read-only), and visualizes the results
4. Try more questions:
   - *"Which persons are connected to organizations in BVI?"*
   - *"Find all circular money flows involving more than 3 accounts"*
   - *"What is the shortest path between Kovacs and Yamamoto?"*
5. Click **"Show Cypher"** to see the generated query for any result

## Key API Queries

```bash
# Find all paths between Kovacs and any account
curl "http://localhost:8000/api/analysis/paths?source=p-kovacs&target=a-kovacs-personal"

# Detect circular money flows
curl "http://localhost:8000/api/analysis/patterns/circular-flows"

# Compute risk for Golden Gate Holdings
curl "http://localhost:8000/api/analysis/risk/o-golden-gate"

# Get graph statistics
curl "http://localhost:8000/api/analysis/stats"

# Trace money from the main laundering account
curl "http://localhost:8000/api/analysis/money-flow?source=a-gg-main"

# --- Temporal Analysis ---

# Get the date range of temporal data (2010-01-01 to 2021-09-01)
curl "http://localhost:8000/api/temporal/date-range"

# View the graph as it existed on 2016-06-15
curl "http://localhost:8000/api/temporal/graph-at?date=2016-06-15"

# See what changed between 2016 and 2019 (core laundering period)
curl "http://localhost:8000/api/temporal/changes?start=2016-01-01&end=2019-01-01"

# Get all dated relationships in chronological order
curl "http://localhost:8000/api/temporal/timeline"

# Get Kovacs's temporal profile
curl "http://localhost:8000/api/temporal/entity/p-kovacs"

# --- Snapshots & Diff ---

# Create a snapshot of the current graph
curl -X POST "http://localhost:8000/api/snapshots/?investigation_id=inv-demo&name=Full%20Network"

# List all snapshots
curl "http://localhost:8000/api/snapshots/"

# Diff two snapshots (replace with actual snapshot IDs)
curl "http://localhost:8000/api/snapshots/diff/compare?snapshot_a=SNAP_ID_1&snapshot_b=SNAP_ID_2"

# Diff current graph vs a snapshot
curl "http://localhost:8000/api/snapshots/diff/current?snapshot_id=SNAP_ID_1"

# --- Natural Language Query (requires LLM_API_KEY) ---

# Ask a question in plain English
curl -X POST "http://localhost:8000/api/nlq/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "Show me all money flows from Kovacs to accounts in Panama"}'

# Get example queries
curl "http://localhost:8000/api/nlq/examples"

# Translate to Cypher without executing
curl -X POST "http://localhost:8000/api/nlq/translate" \
  -H "Content-Type: application/json" \
  -d '{"question": "Who directs organizations in the BVI?"}'
```

## Seed Data Summary

| Entity Type | Count | Examples |
|-------------|-------|---------|
| Persons | 15 | Politicians, lawyers, nominees, bankers |
| Organizations | 15 | Shell companies, trusts, banks across 10 jurisdictions |
| Accounts | 18 | Bank accounts, crypto wallets |
| Addresses | 8 | BVI, Cayman, Panama, Zurich, London... |
| Properties | 5 | Yacht, penthouse, private jet, art collection |
| Events | 6 | Contract awards, sanctions, arrests |
| Documents | 4 | Contracts, SARs, audit reports |
| **Relationships** | **117** | Ownership, transfers, directorships, contacts |
