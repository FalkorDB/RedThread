#!/usr/bin/env python3
"""Performance benchmarks for RedThread's core graph queries.

Requires a running FalkorDB instance seeded with demo data.
Run: python -m benchmarks.run_benchmarks
"""

from __future__ import annotations

import statistics
import time
from typing import Any

import structlog

from src.config import settings
from src.database.falkordb_client import FalkorDBClient
from src.graph import analytics, pathfinding, patterns, risk_scoring, temporal

logger = structlog.get_logger(__name__)


def _timed(fn: Any, *args: Any, **kwargs: Any) -> tuple[Any, float]:
    """Run fn and return (result, elapsed_seconds)."""
    start = time.perf_counter()
    result = fn(*args, **kwargs)
    elapsed = time.perf_counter() - start
    return result, elapsed


def _run_n(n: int, fn: Any, *args: Any, **kwargs: Any) -> dict[str, float]:
    """Run fn n times and return timing statistics."""
    times: list[float] = []
    result = None
    for _ in range(n):
        result, elapsed = _timed(fn, *args, **kwargs)
        times.append(elapsed)
    return {
        "min_ms": min(times) * 1000,
        "max_ms": max(times) * 1000,
        "mean_ms": statistics.mean(times) * 1000,
        "median_ms": statistics.median(times) * 1000,
        "stdev_ms": statistics.stdev(times) * 1000 if len(times) > 1 else 0.0,
        "runs": n,
        "result_size": _result_size(result),
    }


def _result_size(result: Any) -> int:
    """Best-effort count of result items."""
    if isinstance(result, list):
        return len(result)
    if isinstance(result, dict):
        return len(result)
    return 0


def run_all(client: FalkorDBClient, iterations: int = 5) -> list[dict[str, Any]]:
    """Run all benchmarks and return results."""
    benchmarks: list[dict[str, Any]] = []

    def _bench(name: str, category: str, fn: Any, *args: Any, **kwargs: Any) -> None:
        try:
            stats = _run_n(iterations, fn, *args, **kwargs)
            benchmarks.append({"name": name, "category": category, **stats})
        except Exception as exc:
            benchmarks.append({"name": name, "category": category, "error": str(exc)})

    # --- Pattern Detection ---
    _bench(
        "detect_circular_flows",
        "pattern",
        patterns.detect_circular_flows,
        client,
        min_amount=1000,
        limit=20,
    )
    _bench(
        "detect_shell_company_chains",
        "pattern",
        patterns.detect_shell_company_chains,
        client,
        min_depth=2,
        limit=20,
    )
    _bench(
        "detect_structuring",
        "pattern",
        patterns.detect_structuring,
        client,
        threshold=10000,
        min_count=2,
        limit=20,
    )
    _bench(
        "detect_rapid_passthrough",
        "pattern",
        patterns.detect_rapid_passthrough,
        client,
        min_amount=1000,
        limit=20,
    )
    _bench(
        "detect_hidden_connections",
        "pattern",
        patterns.detect_hidden_connections,
        client,
        entity_id_1="p-kovacs",
        entity_id_2="p-chen",
        limit=10,
    )

    # --- Pathfinding ---
    _bench(
        "find_all_paths",
        "pathfinding",
        pathfinding.find_all_paths,
        client,
        source_id="p-kovacs",
        target_id="p-santos",
        max_depth=6,
        limit=20,
    )
    _bench(
        "find_shortest_path",
        "pathfinding",
        pathfinding.find_shortest_path,
        client,
        source_id="p-kovacs",
        target_id="p-santos",
    )
    _bench(
        "trace_money_flow_targeted",
        "pathfinding",
        pathfinding.trace_money_flow,
        client,
        source_id="a-gg-main",
        target_id="a-cerulean",
        min_amount=100,
        limit=20,
    )
    _bench(
        "trace_money_flow_downstream",
        "pathfinding",
        pathfinding.trace_money_flow,
        client,
        source_id="a-gg-main",
        min_amount=100,
        limit=20,
    )
    _bench(
        "find_entity_reach",
        "pathfinding",
        pathfinding.find_entity_reach,
        client,
        entity_id="p-kovacs",
        max_depth=3,
        limit=50,
    )

    # --- Analytics ---
    _bench(
        "degree_centrality",
        "analytics",
        analytics.degree_centrality,
        client,
        limit=20,
    )
    _bench(
        "betweenness_proxy",
        "analytics",
        analytics.betweenness_proxy,
        client,
        limit=20,
    )
    _bench(
        "shared_connections",
        "analytics",
        analytics.shared_connections,
        client,
        entity_id_1="p-kovacs",
        entity_id_2="p-santos",
        limit=20,
    )
    _bench(
        "graph_summary",
        "analytics",
        analytics.graph_summary,
        client,
    )

    # --- Risk Scoring ---
    _bench(
        "compute_entity_risk",
        "risk",
        risk_scoring.compute_entity_risk,
        client,
        entity_id="p-kovacs",
    )
    _bench(
        "compute_network_risk",
        "risk",
        risk_scoring.compute_network_risk,
        client,
        entity_ids=["p-kovacs", "p-chen", "p-santos"],
    )
    _bench(
        "get_highest_risk_entities",
        "risk",
        risk_scoring.get_highest_risk_entities,
        client,
        limit=10,
    )

    # --- Temporal ---
    _bench(
        "get_graph_at_time",
        "temporal",
        temporal.get_graph_at_time,
        client,
        point_in_time="2024-06-01",
        limit=100,
    )
    _bench(
        "get_changes_between",
        "temporal",
        temporal.get_changes_between,
        client,
        start_date="2023-01-01",
        end_date="2024-12-31",
        limit=100,
    )

    return benchmarks


def print_report(results: list[dict[str, Any]]) -> None:
    """Print a formatted benchmark report."""
    print("\n" + "=" * 85)
    print("  RedThread Performance Benchmark Report")
    print("=" * 85)

    categories = sorted(set(r["category"] for r in results))
    for cat in categories:
        cat_results = [r for r in results if r["category"] == cat]
        print(f"\n  [{cat.upper()}]")
        print(f"  {'Query':<35} {'Median':>10} {'Mean':>10} {'Min':>10} {'Max':>10} {'Rows':>6}")
        print(f"  {'-' * 35} {'-' * 10} {'-' * 10} {'-' * 10} {'-' * 10} {'-' * 6}")
        for r in cat_results:
            if "error" in r:
                print(f"  {r['name']:<35} {'ERROR: ' + r['error'][:40]}")
            else:
                print(
                    f"  {r['name']:<35} "
                    f"{r['median_ms']:>8.2f}ms "
                    f"{r['mean_ms']:>8.2f}ms "
                    f"{r['min_ms']:>8.2f}ms "
                    f"{r['max_ms']:>8.2f}ms "
                    f"{r['result_size']:>6}"
                )

    print("\n" + "=" * 85)
    ok = [r for r in results if "error" not in r]
    err = [r for r in results if "error" in r]
    print(f"  Total: {len(results)} benchmarks | {len(ok)} succeeded | {len(err)} errored")
    if ok:
        slowest = max(ok, key=lambda r: r["median_ms"])
        fastest = min(ok, key=lambda r: r["median_ms"])
        print(f"  Slowest: {slowest['name']} ({slowest['median_ms']:.2f}ms median)")
        print(f"  Fastest: {fastest['name']} ({fastest['median_ms']:.2f}ms median)")
    print("=" * 85 + "\n")


def main() -> None:
    """Run benchmarks against the seeded demo graph."""
    client = FalkorDBClient(
        host=settings.falkordb_host,
        port=settings.falkordb_port,
        graph_name=settings.falkordb_graph_name,
    )
    client.connect()

    # Ensure graph has data
    try:
        result = client.ro_query("MATCH (n) RETURN count(n)")
        count = result.result_set[0][0] if result.result_set else 0
    except Exception:
        count = 0

    if count == 0:
        print("Graph is empty — seeding demo data...")
        from src.seed import seed

        seed(client)

    print(f"Graph has {count} nodes. Running benchmarks (5 iterations each)...")
    results = run_all(client, iterations=5)
    print_report(results)


if __name__ == "__main__":
    main()
