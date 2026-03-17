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
