"""Seed data generator — creates a realistic financial investigation network.

This generates a complex web of persons, organizations, accounts, and transactions
that demonstrates money laundering patterns, shell company chains, and hidden connections.

The scenario: "Operation Crimson Tide" — an investigation into a corruption network
involving politicians, shell companies across multiple jurisdictions, and
suspicious financial flows.
"""

from __future__ import annotations

import json

from src.config import settings
from src.database.falkordb_client import FalkorDBClient
from src.database.schema import setup_schema
from src.graph.queries import create_entity, create_relationship


def seed(client: FalkorDBClient) -> dict:
    """Seed the graph with realistic investigation data."""
    print("🔴 RedThread — Seeding investigation data...")
    print("   Scenario: Operation Crimson Tide\n")

    ids: dict[str, str] = {}

    # === PERSONS ===
    persons = [
        {
            "id": "p-kovacs",
            "name": "Viktor Kovacs",
            "nationality": "Hungary",
            "role": "Politician",
            "risk_score": 75,
            "dob": "1968-03-15",
            "notes": "Former Minister of Infrastructure, suspected corruption",
        },
        {
            "id": "p-chen",
            "name": "Li Wei Chen",
            "nationality": "China",
            "role": "Businessman",
            "risk_score": 60,
            "dob": "1972-08-22",
        },
        {
            "id": "p-santos",
            "name": "Maria Santos",
            "nationality": "Brazil",
            "role": "Lawyer",
            "risk_score": 45,
            "dob": "1980-11-03",
            "notes": "Corporate lawyer specializing in offshore structures",
        },
        {
            "id": "p-devries",
            "name": "Pieter de Vries",
            "nationality": "Netherlands",
            "role": "Accountant",
            "risk_score": 50,
            "dob": "1975-06-18",
        },
        {
            "id": "p-okafor",
            "name": "Chukwuma Okafor",
            "nationality": "Nigeria",
            "role": "Oil Executive",
            "risk_score": 55,
            "dob": "1965-01-30",
        },
        {
            "id": "p-mueller",
            "name": "Hans Mueller",
            "nationality": "Germany",
            "role": "Banker",
            "risk_score": 30,
            "dob": "1970-09-12",
        },
        {
            "id": "p-petrova",
            "name": "Anastasia Petrova",
            "nationality": "Russia",
            "role": "Investor",
            "risk_score": 65,
            "dob": "1985-04-25",
        },
        {
            "id": "p-walsh",
            "name": "Declan Walsh",
            "nationality": "Ireland",
            "role": "Nominee Director",
            "risk_score": 70,
            "dob": "1958-12-07",
            "notes": "Professional nominee director, linked to 40+ shell companies",
        },
        {
            "id": "p-kim",
            "name": "Ji-Yeon Kim",
            "nationality": "South Korea",
            "role": "Tech Entrepreneur",
            "risk_score": 20,
            "dob": "1990-02-14",
        },
        {
            "id": "p-rossi",
            "name": "Luca Rossi",
            "nationality": "Italy",
            "role": "Real Estate Developer",
            "risk_score": 40,
            "dob": "1973-07-08",
        },
        {
            "id": "p-ndelu",
            "name": "Themba Ndelu",
            "nationality": "South Africa",
            "role": "Mining Executive",
            "risk_score": 50,
            "dob": "1971-05-20",
        },
        {
            "id": "p-al-rashid",
            "name": "Samir Al-Rashid",
            "nationality": "UAE",
            "role": "Shipping Magnate",
            "risk_score": 55,
            "dob": "1967-11-11",
        },
        {
            "id": "p-garcia",
            "name": "Isabella Garcia",
            "nationality": "Panama",
            "role": "Company Formation Agent",
            "risk_score": 60,
            "dob": "1982-03-28",
        },
        {
            "id": "p-jones",
            "name": "Robert Jones",
            "nationality": "United Kingdom",
            "role": "Compliance Officer",
            "risk_score": 10,
            "dob": "1978-08-16",
            "notes": "Whistleblower who first reported suspicious activity",
        },
        {
            "id": "p-yamamoto",
            "name": "Kenji Yamamoto",
            "nationality": "Japan",
            "role": "Investment Fund Manager",
            "risk_score": 35,
            "dob": "1976-01-22",
        },
    ]

    print(f"   Creating {len(persons)} persons...")
    for p in persons:
        p["aliases"] = json.dumps(p.get("aliases", []))
        create_entity(client, "Person", p)
        ids[p["id"]] = p["id"]

    # === ORGANIZATIONS ===
    organizations = [
        {
            "id": "o-golden-gate",
            "name": "Golden Gate Holdings Ltd",
            "org_type": "company",
            "jurisdiction": "British Virgin Islands",
            "status": "active",
            "risk_score": 70,
        },
        {
            "id": "o-cerulean",
            "name": "Cerulean Trust",
            "org_type": "trust",
            "jurisdiction": "Cayman Islands",
            "status": "active",
            "risk_score": 65,
        },
        {
            "id": "o-nova-infra",
            "name": "Nova Infrastructure Group",
            "org_type": "company",
            "jurisdiction": "Hungary",
            "status": "active",
            "risk_score": 40,
        },
        {
            "id": "o-pacific-rim",
            "name": "Pacific Rim Trading Co",
            "org_type": "company",
            "jurisdiction": "Singapore",
            "status": "active",
            "risk_score": 35,
        },
        {
            "id": "o-atlas-mining",
            "name": "Atlas Mining International",
            "org_type": "company",
            "jurisdiction": "South Africa",
            "status": "active",
            "risk_score": 45,
        },
        {
            "id": "o-crimson-prop",
            "name": "Crimson Properties SA",
            "org_type": "company",
            "jurisdiction": "Panama",
            "status": "active",
            "risk_score": 60,
        },
        {
            "id": "o-rhine-bank",
            "name": "Rhine Commercial Bank AG",
            "org_type": "company",
            "jurisdiction": "Germany",
            "status": "active",
            "risk_score": 15,
        },
        {
            "id": "o-sea-breeze",
            "name": "Sea Breeze Shipping LLC",
            "org_type": "company",
            "jurisdiction": "Malta",
            "status": "active",
            "risk_score": 50,
        },
        {
            "id": "o-emerald-fdn",
            "name": "Emerald Foundation",
            "org_type": "foundation",
            "jurisdiction": "Seychelles",
            "status": "active",
            "risk_score": 55,
            "notes": "Ostensibly charitable, no visible charitable activities",
        },
        {
            "id": "o-northwind",
            "name": "Northwind Consulting AG",
            "org_type": "company",
            "jurisdiction": "Switzerland",
            "status": "active",
            "risk_score": 30,
        },
        {
            "id": "o-dragon-inv",
            "name": "Dragon Investment Partners",
            "org_type": "company",
            "jurisdiction": "Hong Kong",
            "status": "active",
            "risk_score": 40,
        },
        {
            "id": "o-sunset-re",
            "name": "Sunset Real Estate Inc",
            "org_type": "company",
            "jurisdiction": "Cyprus",
            "status": "active",
            "risk_score": 45,
        },
        {
            "id": "o-titan-oil",
            "name": "Titan Oil & Gas Corp",
            "org_type": "company",
            "jurisdiction": "Nigeria",
            "status": "active",
            "risk_score": 50,
        },
        {
            "id": "o-alpine-wm",
            "name": "Alpine Wealth Management",
            "org_type": "company",
            "jurisdiction": "Liechtenstein",
            "status": "active",
            "risk_score": 35,
        },
        {
            "id": "o-phantom-svcs",
            "name": "Phantom Services Ltd",
            "org_type": "shell",
            "jurisdiction": "Belize",
            "status": "dissolved",
            "risk_score": 85,
            "notes": "No employees, no physical office, dissolved after single year",
        },
    ]

    print(f"   Creating {len(organizations)} organizations...")
    for o in organizations:
        create_entity(client, "Organization", o)
        ids[o["id"]] = o["id"]

    # === ACCOUNTS ===
    accounts = [
        {
            "id": "a-gg-main",
            "account_number": "GG-001-MAIN",
            "account_type": "bank",
            "institution": "Rhine Commercial Bank",
            "currency": "EUR",
            "status": "active",
        },
        {
            "id": "a-gg-ops",
            "account_number": "GG-002-OPS",
            "account_type": "bank",
            "institution": "Rhine Commercial Bank",
            "currency": "USD",
            "status": "active",
        },
        {
            "id": "a-cerulean",
            "account_number": "CER-100-TRUST",
            "account_type": "bank",
            "institution": "Cayman National Bank",
            "currency": "USD",
            "status": "active",
        },
        {
            "id": "a-nova-huf",
            "account_number": "NOVA-HU-001",
            "account_type": "bank",
            "institution": "OTP Bank",
            "currency": "HUF",
            "status": "active",
        },
        {
            "id": "a-pacific",
            "account_number": "PRT-SG-001",
            "account_type": "bank",
            "institution": "DBS Bank",
            "currency": "SGD",
            "status": "active",
        },
        {
            "id": "a-atlas",
            "account_number": "ATL-ZA-001",
            "account_type": "bank",
            "institution": "Standard Bank",
            "currency": "ZAR",
            "status": "active",
        },
        {
            "id": "a-crimson",
            "account_number": "CRIM-PA-001",
            "account_type": "bank",
            "institution": "Banco Nacional de Panama",
            "currency": "USD",
            "status": "active",
        },
        {
            "id": "a-seabreeze",
            "account_number": "SBS-MT-001",
            "account_type": "bank",
            "institution": "Bank of Valletta",
            "currency": "EUR",
            "status": "active",
        },
        {
            "id": "a-emerald",
            "account_number": "EMR-SC-001",
            "account_type": "bank",
            "institution": "Barclays Seychelles",
            "currency": "USD",
            "status": "active",
        },
        {
            "id": "a-kovacs-personal",
            "account_number": "VK-PERSONAL-001",
            "account_type": "bank",
            "institution": "OTP Bank",
            "currency": "HUF",
            "status": "active",
        },
        {
            "id": "a-chen-hk",
            "account_number": "LWC-HK-001",
            "account_type": "bank",
            "institution": "HSBC Hong Kong",
            "currency": "HKD",
            "status": "active",
        },
        {
            "id": "a-phantom",
            "account_number": "PHT-BZ-001",
            "account_type": "bank",
            "institution": "Belize Bank",
            "currency": "USD",
            "status": "frozen",
            "risk_score": 80,
        },
        {
            "id": "a-alpine",
            "account_number": "ALP-LI-001",
            "account_type": "bank",
            "institution": "LGT Bank",
            "currency": "CHF",
            "status": "active",
        },
        {
            "id": "a-crypto-1",
            "account_number": "0xABCD1234DEAD5678",
            "account_type": "crypto",
            "institution": "Unknown Exchange",
            "currency": "BTC",
            "status": "active",
            "risk_score": 70,
        },
        {
            "id": "a-northwind",
            "account_number": "NW-CH-001",
            "account_type": "bank",
            "institution": "Credit Suisse",
            "currency": "CHF",
            "status": "active",
        },
        {
            "id": "a-dragon",
            "account_number": "DRG-HK-001",
            "account_type": "bank",
            "institution": "Bank of China HK",
            "currency": "HKD",
            "status": "active",
        },
        {
            "id": "a-sunset",
            "account_number": "SST-CY-001",
            "account_type": "bank",
            "institution": "Bank of Cyprus",
            "currency": "EUR",
            "status": "active",
        },
        {
            "id": "a-titan",
            "account_number": "TTN-NG-001",
            "account_type": "bank",
            "institution": "First Bank Nigeria",
            "currency": "NGN",
            "status": "active",
        },
    ]

    print(f"   Creating {len(accounts)} accounts...")
    for a in accounts:
        create_entity(client, "Account", a)
        ids[a["id"]] = a["id"]

    # === ADDRESSES ===
    addresses = [
        {
            "id": "addr-bvi",
            "full_address": "Craigmuir Chambers, Road Town",
            "city": "Road Town",
            "country": "British Virgin Islands",
            "postal_code": "VG1110",
        },
        {
            "id": "addr-cayman",
            "full_address": "George Town, Grand Cayman",
            "city": "George Town",
            "country": "Cayman Islands",
        },
        {
            "id": "addr-budapest",
            "full_address": "Andrassy ut 60, Budapest",
            "city": "Budapest",
            "country": "Hungary",
            "postal_code": "1062",
        },
        {
            "id": "addr-panama",
            "full_address": "Torre Global Bank, Calle 50, Panama City",
            "city": "Panama City",
            "country": "Panama",
        },
        {
            "id": "addr-zurich",
            "full_address": "Bahnhofstrasse 42, Zurich",
            "city": "Zurich",
            "country": "Switzerland",
            "postal_code": "8001",
        },
        {
            "id": "addr-london",
            "full_address": "1 Canary Wharf, London",
            "city": "London",
            "country": "United Kingdom",
            "postal_code": "E14 5AB",
        },
        {
            "id": "addr-hk",
            "full_address": "Two IFC, Central, Hong Kong",
            "city": "Hong Kong",
            "country": "China",
        },
        {
            "id": "addr-lagos",
            "full_address": "Victoria Island, Lagos",
            "city": "Lagos",
            "country": "Nigeria",
        },
    ]

    print(f"   Creating {len(addresses)} addresses...")
    for a in addresses:
        create_entity(client, "Address", a)
        ids[a["id"]] = a["id"]

    # === PROPERTIES ===
    properties = [
        {
            "id": "prop-yacht",
            "property_type": "yacht",
            "description": "M/Y 'Crimson Dawn' - 65m superyacht",
            "value": 35000000,
            "currency": "EUR",
            "location": "Monaco",
        },
        {
            "id": "prop-penthouse",
            "property_type": "real_estate",
            "description": "Penthouse apartment, Knightsbridge, London",
            "value": 22000000,
            "currency": "GBP",
            "location": "London, UK",
        },
        {
            "id": "prop-villa",
            "property_type": "real_estate",
            "description": "Villa on Lake Balaton, Hungary",
            "value": 3500000,
            "currency": "EUR",
            "location": "Balaton, Hungary",
        },
        {
            "id": "prop-jet",
            "property_type": "aircraft",
            "description": "Gulfstream G650ER private jet",
            "value": 65000000,
            "currency": "USD",
            "location": "Various",
        },
        {
            "id": "prop-art",
            "property_type": "art",
            "description": "Collection of impressionist paintings",
            "value": 12000000,
            "currency": "USD",
            "location": "Zurich freeport",
        },
    ]

    print(f"   Creating {len(properties)} properties...")
    for p in properties:
        create_entity(client, "Property", p)
        ids[p["id"]] = p["id"]

    # === EVENTS ===
    events = [
        {
            "id": "ev-contract",
            "event_type": "filing",
            "date": "2019-06-15",
            "description": "Highway construction contract awarded to Nova Infrastructure - €450M",
            "amount": 450000000,
            "currency": "EUR",
            "location": "Budapest",
        },
        {
            "id": "ev-meeting-1",
            "event_type": "meeting",
            "date": "2019-05-20",
            "description": "Private meeting at Hotel Kempinski, Budapest",
            "location": "Budapest",
        },
        {
            "id": "ev-sanction",
            "event_type": "sanction",
            "date": "2023-09-01",
            "description": "EU sanctions screening flagged Golden Gate Holdings",
            "location": "Brussels",
        },
        {
            "id": "ev-arrest",
            "event_type": "arrest",
            "date": "2024-03-15",
            "description": "Arrest warrant issued for Viktor Kovacs",
            "location": "Budapest",
        },
        {
            "id": "ev-dissolution",
            "event_type": "filing",
            "date": "2021-12-01",
            "description": "Phantom Services Ltd voluntarily dissolved",
            "location": "Belize City",
        },
        {
            "id": "ev-whistleblow",
            "event_type": "communication",
            "date": "2023-01-10",
            "description": "Anonymous tip received by compliance team at Rhine Commercial Bank",
            "location": "Frankfurt",
        },
    ]

    print(f"   Creating {len(events)} events...")
    for e in events:
        create_entity(client, "Event", e)
        ids[e["id"]] = e["id"]

    # === DOCUMENTS ===
    documents = [
        {
            "id": "doc-contract",
            "doc_type": "contract",
            "date": "2019-06-15",
            "title": "Highway M8 Construction Contract",
            "source": "Hungarian Government Gazette",
            "summary": "€450M contract for M8 highway extension",
        },
        {
            "id": "doc-sar",
            "doc_type": "report",
            "date": "2023-01-15",
            "title": "Suspicious Activity Report #2023-0042",
            "source": "Rhine Commercial Bank",
            "summary": "SAR filed regarding unusual transaction patterns in Golden Gate Holdings accounts",
        },
        {
            "id": "doc-incorporation",
            "doc_type": "filing",
            "date": "2018-03-01",
            "title": "Certificate of Incorporation - Phantom Services Ltd",
            "source": "Belize Companies Registry",
        },
        {
            "id": "doc-audit",
            "doc_type": "report",
            "date": "2023-06-20",
            "title": "Forensic Audit Report - Nova Infrastructure",
            "source": "KPMG Hungary",
            "summary": "Identified €23M in unexplained payments to offshore entities",
        },
    ]

    print(f"   Creating {len(documents)} documents...")
    for d in documents:
        create_entity(client, "Document", d)
        ids[d["id"]] = d["id"]

    # === RELATIONSHIPS ===
    print("\n   Creating relationships...")

    # Build date lookups for entities that have dates, so we can set
    # valid_from on relationships that lack their own since/date field.
    _entity_dates: dict[str, str] = {}
    for e in events:
        if e.get("date"):
            _entity_dates[e["id"]] = e["date"]
    for d in documents:
        if d.get("date"):
            _entity_dates[d["id"]] = d["date"]

    def _add_temporal(props: dict, default_from: str | None = None) -> dict:
        """Auto-populate valid_from/valid_to from since/until if not set."""
        if "valid_from" not in props:
            props["valid_from"] = props.get("since") or props.get("date") or default_from or ""
        if "valid_to" not in props and "until" in props and props["until"]:
            props["valid_to"] = props["until"]
        return props

    # Directs (Person → Organization)
    directs = [
        (
            "p-kovacs",
            "o-nova-infra",
            {"role": "chairman", "since": "2015-01-01", "until": "2020-03-15"},
        ),
        ("p-walsh", "o-golden-gate", {"role": "nominee director", "since": "2018-06-01"}),
        ("p-walsh", "o-cerulean", {"role": "nominee trustee", "since": "2018-06-15"}),
        (
            "p-walsh",
            "o-phantom-svcs",
            {"role": "nominee director", "since": "2018-03-01", "until": "2020-06-01"},
        ),
        ("p-santos", "o-crimson-prop", {"role": "director", "since": "2017-01-01"}),
        ("p-chen", "o-pacific-rim", {"role": "managing director", "since": "2012-05-01"}),
        ("p-chen", "o-dragon-inv", {"role": "chairman", "since": "2016-03-01"}),
        ("p-okafor", "o-titan-oil", {"role": "CEO", "since": "2010-01-01"}),
        (
            "p-ndelu",
            "o-atlas-mining",
            {"role": "director", "since": "2014-07-01", "until": "2021-01-01"},
        ),
        ("p-al-rashid", "o-sea-breeze", {"role": "owner", "since": "2011-01-01"}),
        ("p-rossi", "o-sunset-re", {"role": "managing director", "since": "2016-06-01"}),
        ("p-devries", "o-northwind", {"role": "partner", "since": "2013-01-01"}),
        (
            "p-mueller",
            "o-rhine-bank",
            {"role": "VP compliance", "since": "2018-01-01", "until": "2020-12-31"},
        ),
        ("p-garcia", "o-phantom-svcs", {"role": "formation agent", "since": "2018-03-01"}),
        ("p-yamamoto", "o-alpine-wm", {"role": "fund manager", "since": "2019-01-01"}),
    ]

    for src, tgt, props in directs:
        create_relationship(
            client, "Person", src, "Organization", tgt, "DIRECTS", _add_temporal(props)
        )

    # Owns (ownership chains)
    owns = [
        (
            "p-kovacs",
            "Person",
            "o-golden-gate",
            "Organization",
            {
                "share_pct": 100,
                "since": "2018-06-01",
                "notes": "Beneficial owner through nominee structure",
            },
        ),
        (
            "o-golden-gate",
            "Organization",
            "o-cerulean",
            "Organization",
            {"share_pct": 100, "since": "2018-06-15"},
        ),
        (
            "o-cerulean",
            "Organization",
            "o-crimson-prop",
            "Organization",
            {"share_pct": 80, "since": "2018-07-01"},
        ),
        (
            "o-golden-gate",
            "Organization",
            "o-phantom-svcs",
            "Organization",
            {"share_pct": 100, "since": "2018-03-01"},
        ),
        (
            "p-chen",
            "Person",
            "o-dragon-inv",
            "Organization",
            {"share_pct": 60, "since": "2016-03-01"},
        ),
        (
            "o-pacific-rim",
            "Organization",
            "o-sea-breeze",
            "Organization",
            {"share_pct": 40, "since": "2019-01-01"},
        ),
        (
            "p-al-rashid",
            "Person",
            "o-sea-breeze",
            "Organization",
            {"share_pct": 60, "since": "2011-01-01"},
        ),
        ("o-golden-gate", "Organization", "a-gg-main", "Account", {"since": "2018-06-01"}),
        ("o-golden-gate", "Organization", "a-gg-ops", "Account", {"since": "2018-06-01"}),
        ("o-cerulean", "Organization", "a-cerulean", "Account", {"since": "2018-06-15"}),
        ("o-nova-infra", "Organization", "a-nova-huf", "Account", {"since": "2015-01-01"}),
        ("o-pacific-rim", "Organization", "a-pacific", "Account", {"since": "2012-05-01"}),
        ("o-atlas-mining", "Organization", "a-atlas", "Account", {"since": "2014-07-01"}),
        ("o-crimson-prop", "Organization", "a-crimson", "Account", {"since": "2017-01-01"}),
        ("o-sea-breeze", "Organization", "a-seabreeze", "Account", {"since": "2011-01-01"}),
        ("o-emerald-fdn", "Organization", "a-emerald", "Account", {"since": "2019-01-01"}),
        ("p-kovacs", "Person", "a-kovacs-personal", "Account", {"since": "2010-01-01"}),
        ("p-chen", "Person", "a-chen-hk", "Account", {"since": "2012-01-01"}),
        ("o-phantom-svcs", "Organization", "a-phantom", "Account", {"since": "2018-03-01"}),
        ("o-alpine-wm", "Organization", "a-alpine", "Account", {"since": "2019-01-01"}),
        ("o-northwind", "Organization", "a-northwind", "Account", {"since": "2013-01-01"}),
        ("o-dragon-inv", "Organization", "a-dragon", "Account", {"since": "2016-03-01"}),
        ("o-sunset-re", "Organization", "a-sunset", "Account", {"since": "2016-06-01"}),
        ("o-titan-oil", "Organization", "a-titan", "Account", {"since": "2010-01-01"}),
        # Property ownership
        (
            "p-kovacs",
            "Person",
            "prop-yacht",
            "Property",
            {"since": "2020-03-01", "notes": "Registered through Golden Gate Holdings"},
        ),
        ("o-crimson-prop", "Organization", "prop-penthouse", "Property", {"since": "2019-08-01"}),
        ("p-kovacs", "Person", "prop-villa", "Property", {"since": "2016-01-01"}),
        ("o-cerulean", "Organization", "prop-jet", "Property", {"since": "2020-06-01"}),
        ("o-alpine-wm", "Organization", "prop-art", "Property", {"since": "2021-01-01"}),
    ]

    for src, src_label, tgt, tgt_label, props in owns:
        create_relationship(client, src_label, src, tgt_label, tgt, "OWNS", _add_temporal(props))

    # Subsidiary chains
    subsidiaries = [
        ("o-crimson-prop", "o-golden-gate", {"ownership_pct": 100, "since": "2018-07-01"}),
        ("o-phantom-svcs", "o-cerulean", {"ownership_pct": 100, "since": "2018-03-15"}),
        ("o-emerald-fdn", "o-crimson-prop", {"ownership_pct": 100, "since": "2019-01-01"}),
        ("o-sea-breeze", "o-pacific-rim", {"ownership_pct": 40, "since": "2019-01-01"}),
        ("o-sunset-re", "o-dragon-inv", {"ownership_pct": 30, "since": "2018-01-01"}),
    ]

    for src, tgt, props in subsidiaries:
        create_relationship(
            client, "Organization", src, "Organization", tgt, "SUBSIDIARY_OF", _add_temporal(props)
        )

    # Money transfers — the heart of the investigation
    transfers = [
        # Main corruption flow: Government → Nova → Golden Gate → offshore → back
        (
            "a-nova-huf",
            "a-gg-main",
            {
                "amount": 23000000,
                "currency": "EUR",
                "date": "2019-07-15",
                "reference": "Consulting fees",
            },
        ),
        (
            "a-gg-main",
            "a-cerulean",
            {
                "amount": 15000000,
                "currency": "USD",
                "date": "2019-07-20",
                "reference": "Investment transfer",
            },
        ),
        (
            "a-gg-main",
            "a-phantom",
            {
                "amount": 5000000,
                "currency": "USD",
                "date": "2019-07-22",
                "reference": "Service fees",
            },
        ),
        (
            "a-cerulean",
            "a-crimson",
            {
                "amount": 8000000,
                "currency": "USD",
                "date": "2019-08-01",
                "reference": "Property acquisition",
            },
        ),
        (
            "a-cerulean",
            "a-emerald",
            {
                "amount": 4000000,
                "currency": "USD",
                "date": "2019-08-15",
                "reference": "Charitable donation",
            },
        ),
        (
            "a-phantom",
            "a-kovacs-personal",
            {
                "amount": 2000000,
                "currency": "USD",
                "date": "2019-09-01",
                "reference": "Consulting payment",
            },
        ),
        # Circular flow (money laundering cycle)
        (
            "a-crimson",
            "a-seabreeze",
            {
                "amount": 3000000,
                "currency": "EUR",
                "date": "2020-01-15",
                "reference": "Shipping services",
            },
        ),
        (
            "a-seabreeze",
            "a-pacific",
            {
                "amount": 2800000,
                "currency": "USD",
                "date": "2020-02-01",
                "reference": "Trade finance",
            },
        ),
        (
            "a-pacific",
            "a-dragon",
            {"amount": 2500000, "currency": "HKD", "date": "2020-02-15", "reference": "Investment"},
        ),
        (
            "a-dragon",
            "a-gg-ops",
            {
                "amount": 2200000,
                "currency": "USD",
                "date": "2020-03-01",
                "reference": "Return on investment",
            },
        ),
        (
            "a-gg-ops",
            "a-crimson",
            {
                "amount": 2000000,
                "currency": "USD",
                "date": "2020-03-15",
                "reference": "Operating costs",
            },
        ),
        # Structuring pattern (multiple transfers just below 10K)
        (
            "a-gg-ops",
            "a-kovacs-personal",
            {
                "amount": 9500,
                "currency": "USD",
                "date": "2020-04-01",
                "reference": "Expense reimbursement",
            },
        ),
        (
            "a-gg-ops",
            "a-kovacs-personal",
            {
                "amount": 9800,
                "currency": "USD",
                "date": "2020-04-05",
                "reference": "Travel expenses",
            },
        ),
        (
            "a-gg-ops",
            "a-kovacs-personal",
            {
                "amount": 9200,
                "currency": "USD",
                "date": "2020-04-10",
                "reference": "Consulting fee",
            },
        ),
        (
            "a-gg-ops",
            "a-kovacs-personal",
            {"amount": 9700, "currency": "USD", "date": "2020-04-15", "reference": "Advisory fee"},
        ),
        (
            "a-gg-ops",
            "a-kovacs-personal",
            {"amount": 9900, "currency": "USD", "date": "2020-04-20", "reference": "Bonus"},
        ),
        # Rapid pass-through
        (
            "a-titan",
            "a-northwind",
            {"amount": 5000000, "currency": "USD", "date": "2020-06-01", "reference": "Consulting"},
        ),
        (
            "a-northwind",
            "a-alpine",
            {
                "amount": 4800000,
                "currency": "CHF",
                "date": "2020-06-02",
                "reference": "Investment management",
            },
        ),
        (
            "a-alpine",
            "a-cerulean",
            {
                "amount": 4500000,
                "currency": "USD",
                "date": "2020-06-03",
                "reference": "Trust deposit",
            },
        ),
        # Cross-network flow
        (
            "a-chen-hk",
            "a-dragon",
            {
                "amount": 10000000,
                "currency": "HKD",
                "date": "2019-03-01",
                "reference": "Capital injection",
            },
        ),
        (
            "a-atlas",
            "a-titan",
            {
                "amount": 7000000,
                "currency": "ZAR",
                "date": "2019-05-01",
                "reference": "Joint venture",
            },
        ),
        (
            "a-emerald",
            "a-crypto-1",
            {
                "amount": 1500000,
                "currency": "USD",
                "date": "2021-06-01",
                "reference": "Digital asset purchase",
            },
        ),
        (
            "a-crypto-1",
            "a-sunset",
            {
                "amount": 1400000,
                "currency": "EUR",
                "date": "2021-07-01",
                "reference": "Property investment",
            },
        ),
        # Additional flows for complexity
        (
            "a-sunset",
            "a-alpine",
            {
                "amount": 800000,
                "currency": "EUR",
                "date": "2021-08-01",
                "reference": "Wealth management",
            },
        ),
        (
            "a-alpine",
            "a-gg-main",
            {
                "amount": 700000,
                "currency": "CHF",
                "date": "2021-09-01",
                "reference": "Fund distribution",
            },
        ),
    ]

    print(f"   Creating {len(transfers)} financial transfers...")
    for src, tgt, props in transfers:
        create_relationship(
            client, "Account", src, "Account", tgt, "TRANSFERRED_TO", _add_temporal(props)
        )

    # Located at
    locations = [
        (
            "p-kovacs",
            "Person",
            "addr-budapest",
            {"addr_type": "residential", "since": "2010-01-01"},
        ),
        (
            "o-golden-gate",
            "Organization",
            "addr-bvi",
            {"addr_type": "registered", "since": "2018-06-01"},
        ),
        (
            "o-cerulean",
            "Organization",
            "addr-cayman",
            {"addr_type": "registered", "since": "2018-06-15"},
        ),
        (
            "o-nova-infra",
            "Organization",
            "addr-budapest",
            {"addr_type": "registered", "since": "2015-01-01"},
        ),
        (
            "o-crimson-prop",
            "Organization",
            "addr-panama",
            {"addr_type": "registered", "since": "2017-01-01"},
        ),
        (
            "o-northwind",
            "Organization",
            "addr-zurich",
            {"addr_type": "registered", "since": "2013-01-01"},
        ),
        ("p-jones", "Person", "addr-london", {"addr_type": "residential", "since": "2015-01-01"}),
        (
            "o-rhine-bank",
            "Organization",
            "addr-london",
            {"addr_type": "operational", "since": "2018-01-01"},
        ),
        ("p-chen", "Person", "addr-hk", {"addr_type": "residential", "since": "2012-01-01"}),
        (
            "o-titan-oil",
            "Organization",
            "addr-lagos",
            {"addr_type": "registered", "since": "2010-01-01"},
        ),
        (
            "o-phantom-svcs",
            "Organization",
            "addr-bvi",
            {
                "addr_type": "registered",
                "since": "2018-03-01",
                "notes": "Same registered address as Golden Gate Holdings",
            },
        ),
    ]

    for src, src_label, tgt, props in locations:
        create_relationship(
            client, src_label, src, "Address", tgt, "LOCATED_AT", _add_temporal(props)
        )

    # Related to (personal connections)
    related = [
        ("p-kovacs", "p-petrova", {"relationship_type": "romantic", "since": "2018-01-01"}),
        ("p-santos", "p-garcia", {"relationship_type": "business", "since": "2016-01-01"}),
        ("p-chen", "p-al-rashid", {"relationship_type": "business", "since": "2015-01-01"}),
        ("p-devries", "p-mueller", {"relationship_type": "associate", "since": "2017-01-01"}),
        ("p-okafor", "p-ndelu", {"relationship_type": "business", "since": "2014-01-01"}),
        ("p-kovacs", "p-walsh", {"relationship_type": "business", "since": "2018-05-01"}),
    ]

    for src, tgt, props in related:
        create_relationship(
            client, "Person", src, "Person", tgt, "RELATED_TO", _add_temporal(props)
        )

    # Contacted
    contacted = [
        ("p-kovacs", "p-chen", {"method": "phone", "date": "2019-05-18", "duration": "45 min"}),
        ("p-kovacs", "p-santos", {"method": "email", "date": "2019-06-01"}),
        (
            "p-santos",
            "p-garcia",
            {"method": "meeting", "date": "2018-02-15", "duration": "2 hours"},
        ),
        ("p-walsh", "p-santos", {"method": "phone", "date": "2018-05-28"}),
        ("p-devries", "p-yamamoto", {"method": "email", "date": "2019-12-01"}),
        (
            "p-kovacs",
            "p-devries",
            {"method": "meeting", "date": "2019-07-10", "duration": "3 hours"},
        ),
    ]

    for src, tgt, props in contacted:
        create_relationship(client, "Person", src, "Person", tgt, "CONTACTED", _add_temporal(props))

    # Participated in events
    participations = [
        ("p-kovacs", "Person", "ev-contract", {"role": "signatory"}),
        ("o-nova-infra", "Organization", "ev-contract", {"role": "contractor"}),
        ("p-kovacs", "Person", "ev-meeting-1", {"role": "attendee"}),
        ("p-chen", "Person", "ev-meeting-1", {"role": "attendee"}),
        ("p-santos", "Person", "ev-meeting-1", {"role": "legal advisor"}),
        ("o-golden-gate", "Organization", "ev-sanction", {"role": "subject"}),
        ("p-kovacs", "Person", "ev-arrest", {"role": "subject"}),
        ("o-phantom-svcs", "Organization", "ev-dissolution", {"role": "subject"}),
        ("p-jones", "Person", "ev-whistleblow", {"role": "reporter"}),
    ]

    for src, src_label, tgt, props in participations:
        create_relationship(
            client,
            src_label,
            src,
            "Event",
            tgt,
            "PARTICIPATED_IN",
            _add_temporal(props, default_from=_entity_dates.get(tgt)),
        )

    # Mentioned in documents
    mentions = [
        (
            "p-kovacs",
            "Person",
            "doc-contract",
            {"context": "Signatory as Minister of Infrastructure"},
        ),
        ("o-nova-infra", "Organization", "doc-contract", {"context": "Awarded contractor"}),
        (
            "o-golden-gate",
            "Organization",
            "doc-sar",
            {"context": "Subject of suspicious activity report"},
        ),
        ("p-jones", "Person", "doc-sar", {"context": "Reporting officer"}),
        ("o-phantom-svcs", "Organization", "doc-incorporation", {"context": "Incorporated entity"}),
        ("p-garcia", "Person", "doc-incorporation", {"context": "Formation agent"}),
        ("o-nova-infra", "Organization", "doc-audit", {"context": "Audited entity"}),
        (
            "o-golden-gate",
            "Organization",
            "doc-audit",
            {"context": "Recipient of unexplained payments"},
        ),
    ]

    for src, src_label, tgt, props in mentions:
        create_relationship(
            client,
            src_label,
            src,
            "Document",
            tgt,
            "MENTIONED_IN",
            _add_temporal(props, default_from=_entity_dates.get(tgt)),
        )

    # Employed by
    employed = [
        (
            "p-jones",
            "o-rhine-bank",
            {"position": "Senior Compliance Officer", "since": "2015-06-01"},
        ),
        ("p-kim", "o-dragon-inv", {"position": "CTO", "since": "2017-01-01"}),
        (
            "p-petrova",
            "o-alpine-wm",
            {"position": "Client Relations Manager", "since": "2019-03-01"},
        ),
    ]

    for src, tgt, props in employed:
        create_relationship(
            client, "Person", src, "Organization", tgt, "EMPLOYED_BY", _add_temporal(props)
        )

    # Print summary
    from src.database.schema import get_graph_stats

    stats = get_graph_stats(client)

    print("\n✅ Seed data loaded successfully!")
    print(f"   Nodes: {stats['total_nodes']}")
    print(f"   Relationships: {stats['total_relationships']}")
    print(f"   Persons: {stats.get('Person', 0)}")
    print(f"   Organizations: {stats.get('Organization', 0)}")
    print(f"   Accounts: {stats.get('Account', 0)}")
    print(f"   Addresses: {stats.get('Address', 0)}")
    print(f"   Properties: {stats.get('Property', 0)}")
    print(f"   Events: {stats.get('Event', 0)}")
    print(f"   Documents: {stats.get('Document', 0)}")
    print("\n🔍 Key investigation entry points:")
    print("   • Viktor Kovacs (p-kovacs) — Main suspect, former minister")
    print("   • Golden Gate Holdings (o-golden-gate) — Primary shell company")
    print("   • Phantom Services (o-phantom-svcs) — Dissolved shell, single-use")
    print("   • Account GG-001-MAIN (a-gg-main) — Primary laundering account")
    print("   • Declan Walsh (p-walsh) — Nominee director across multiple entities")

    return stats


if __name__ == "__main__":
    client = FalkorDBClient(
        host=settings.falkordb_host,
        port=settings.falkordb_port,
        graph_name=settings.falkordb_graph_name,
    )
    client.connect()
    # Clean slate
    client.delete_graph()
    client.connect()
    setup_schema(client)
    seed(client)
