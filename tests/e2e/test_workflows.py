"""End-to-end test: Full investigation workflow."""

from __future__ import annotations


class TestInvestigationWorkflow:
    """Simulates a real user workflow: create entities, link them, investigate."""

    def test_full_investigation_workflow(self, test_client):
        """E2E: Create network → Create investigation → Find paths → Detect patterns."""

        # Step 1: Create entities for a money laundering scenario
        person = test_client.post(
            "/api/entities/person",
            json={
                "name": "E2E Suspect",
                "nationality": "Panama",
                "risk_score": 70,
            },
        ).json()

        org = test_client.post(
            "/api/entities/organization",
            json={
                "name": "E2E Shell Corp",
                "org_type": "company",
                "jurisdiction": "Cayman Islands",
            },
        ).json()

        acct1 = test_client.post(
            "/api/entities/account",
            json={
                "account_number": "E2E-ACC-001",
                "institution": "Offshore Bank",
            },
        ).json()

        acct2 = test_client.post(
            "/api/entities/account",
            json={
                "account_number": "E2E-ACC-002",
                "institution": "Local Bank",
            },
        ).json()

        # Step 2: Create relationships
        test_client.post(
            "/api/relationships/",
            json={
                "source_id": person["id"],
                "target_id": org["id"],
                "source_label": "Person",
                "target_label": "Organization",
                "rel_type": "DIRECTS",
                "properties": {"role": "beneficial owner"},
            },
        )

        test_client.post(
            "/api/relationships/",
            json={
                "source_id": org["id"],
                "target_id": acct1["id"],
                "source_label": "Organization",
                "target_label": "Account",
                "rel_type": "OWNS",
                "properties": {},
            },
        )

        test_client.post(
            "/api/relationships/",
            json={
                "source_id": acct1["id"],
                "target_id": acct2["id"],
                "source_label": "Account",
                "target_label": "Account",
                "rel_type": "TRANSFERRED_TO",
                "properties": {"amount": 500000, "date": "2024-01-01"},
            },
        )

        # Step 3: Create an investigation
        inv = test_client.post(
            "/api/investigations/",
            json={
                "name": "E2E Test Investigation",
                "description": "Testing the full workflow",
            },
        ).json()

        # Step 4: Add entities to investigation
        test_client.post(
            f"/api/investigations/{inv['id']}/entities?entity_id={person['id']}&entity_label=Person"
        )

        # Step 5: Find paths between person and account
        res = test_client.get(f"/api/analysis/paths?source={person['id']}&target={acct2['id']}")
        paths = res.json()
        assert paths["count"] > 0, "Should find at least one path through org and account"

        # Step 6: Compute risk
        risk_res = test_client.get(f"/api/analysis/risk/{person['id']}")
        risk = risk_res.json()
        assert risk["risk_score"] >= 0

        # Step 7: Get neighborhood
        hood_res = test_client.get(f"/api/entities/{person['id']}/neighborhood?depth=2")
        hood = hood_res.json()
        assert len(hood["nodes"]) >= 2  # person and at least org or account

        # Step 8: Export report
        report_res = test_client.get(f"/api/export/report?entity_id={person['id']}")
        report = report_res.json()
        assert "subject" in report
        assert report["direct_connections"] > 0


class TestDataImportWorkflow:
    """Simulates importing data and then analyzing it."""

    def test_json_import_and_analyze(self, test_client):
        """E2E: Import JSON data → Search → Analyze."""

        # Step 1: Import entities and relationships via JSON
        import_data = {
            "entities": [
                {"label": "Person", "properties": {"id": "import-p1", "name": "Import Person 1"}},
                {"label": "Person", "properties": {"id": "import-p2", "name": "Import Person 2"}},
                {"label": "Organization", "properties": {"id": "import-o1", "name": "Import Org"}},
            ],
            "relationships": [
                {
                    "source_id": "import-p1",
                    "target_id": "import-o1",
                    "source_label": "Person",
                    "target_label": "Organization",
                    "rel_type": "DIRECTS",
                    "properties": {},
                },
                {
                    "source_id": "import-p2",
                    "target_id": "import-o1",
                    "source_label": "Person",
                    "target_label": "Organization",
                    "rel_type": "EMPLOYED_BY",
                    "properties": {},
                },
            ],
        }

        res = test_client.post("/api/import/json/inline", json=import_data)
        assert res.status_code == 200
        result = res.json()
        assert result["imported_entities"] == 3
        assert result["imported_relationships"] == 2

        # Step 2: Search for imported entities
        search_res = test_client.get("/api/entities/?q=Import Person")
        assert search_res.json()["total"] >= 1

        # Step 3: Find shared connections
        shared_res = test_client.get(
            "/api/analysis/shared-connections?entity1=import-p1&entity2=import-p2"
        )
        shared = shared_res.json()
        # Both connect to import-o1
        assert len(shared) >= 1
