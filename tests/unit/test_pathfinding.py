"""Unit tests for path finding."""

from __future__ import annotations


class TestPathFinding:
    def test_find_all_paths(self, seeded_graph):
        from src.graph.pathfinding import find_all_paths

        paths = find_all_paths(seeded_graph, "test-p1", "test-p2")
        assert len(paths) > 0
        assert all("nodes" in p and "edges" in p for p in paths)

    def test_shortest_path(self, seeded_graph):
        from src.graph.pathfinding import find_shortest_path

        path = find_shortest_path(seeded_graph, "test-p1", "test-p2")
        assert path is not None
        assert path["length"] >= 1

    def test_no_path_between_disconnected(self, clean_graph):
        from src.graph.pathfinding import find_all_paths
        from src.graph.queries import create_entity

        create_entity(clean_graph, "Person", {"id": "iso-1", "name": "Isolated 1"})
        create_entity(clean_graph, "Person", {"id": "iso-2", "name": "Isolated 2"})

        paths = find_all_paths(clean_graph, "iso-1", "iso-2")
        assert len(paths) == 0

    def test_money_flow_tracing(self, seeded_graph):
        from src.graph.pathfinding import trace_money_flow

        flows = trace_money_flow(seeded_graph, "test-a1", target_id="test-a3")
        assert len(flows) > 0

    def test_entity_reach(self, seeded_graph):
        from src.graph.pathfinding import find_entity_reach

        reach = find_entity_reach(seeded_graph, "test-p1", max_depth=3)
        assert reach["total_reached"] > 0
        assert "by_distance" in reach
