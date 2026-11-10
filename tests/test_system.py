import json, tempfile, unittest
from pathlib import Path
from autumn.core import Memory, Telemetry, run, validate_draft, ROOT


class Fake:
    def __init__(self, answers):
        self.answers = iter(answers)
        self.tiers = []

    def ask(self, tier, *args):
        self.tiers.append(tier)
        return next(self.answers)


class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.m = Memory(Path(self.tmp.name) / "memory.db")
        self.addCleanup(self.m.db.close)
        self.m.ingest(ROOT / "data")
        self.t = Telemetry(Path(self.tmp.name) / "telemetry")

    def execute(self, f, q="What is backup retention?"):
        return run(q, memory=self.m, telemetry=self.t, client=f)

    def test_integrated_approval(self):
        f = Fake(
            [
                {"query": "backup retention", "complex": False},
                {
                    "abstain": False,
                    "claims": [
                        {
                            "source_id": "BACKUP_CURRENT",
                            "quote": "Backup retention is 30 days.",
                        }
                    ],
                },
                {"approved": True, "reason": "Direct answer"},
            ]
        )
        self.assertEqual(self.execute(f)["status"], "approved")
        self.assertEqual(f.tiers, ["small", "medium", "large"])

    def test_temporal_versions(self):
        self.assertEqual(
            [
                r["id"]
                for r in self.m.search_documents("backup retention", "2026-08-31")
            ],
            ["BACKUP_OLD"],
        )
        self.assertEqual(
            [
                r["id"]
                for r in self.m.search_documents("backup retention", "2026-09-01")
            ],
            ["BACKUP_CURRENT"],
        )

    def test_unknown_and_expired_source(self):
        for ident in ["../secret", "BACKUP_OLD", "MISSING"]:
            with self.assertRaises((ValueError, KeyError)):
                self.m.read_section(ident, "2026-11-10")

    def test_fts_injection(self):
        self.m.search_documents('" OR * DROP TABLE sections; --', "2026-11-10")
        self.assertEqual(
            self.m.db.execute("SELECT count(*) FROM sections").fetchone()[0], 7
        )

    def test_quote_tampering(self):
        e = [self.m.read_section("BACKUP_CURRENT", "2026-11-10")]
        self.assertFalse(
            validate_draft(
                {
                    "abstain": False,
                    "claims": [
                        {
                            "source_id": "BACKUP_CURRENT",
                            "quote": "Backup retention is 300 days.",
                        }
                    ],
                },
                e,
            )[0]
        )

    def test_one_repair_then_withhold(self):
        bad = {
            "abstain": False,
            "claims": [
                {"source_id": "NO_SOURCE", "quote": "Fabricated evidence statement."}
            ],
        }
        f = Fake([{"query": "backup", "complex": False}, bad, bad])
        r = self.execute(f)
        self.assertEqual((r["status"], r["repairs"], r["claims"]), ("abstained", 1, []))
        self.assertEqual(f.tiers, ["small", "medium", "large"])

    def test_verifier_blocks_irrelevance(self):
        draft = {
            "abstain": False,
            "claims": [
                {"source_id": "BACKUP_CURRENT", "quote": "Backup retention is 30 days."}
            ],
        }
        f = Fake(
            [
                {"query": "backup", "complex": False},
                draft,
                {"approved": False, "reason": "Irrelevant"},
                draft,
                {"approved": False, "reason": "Irrelevant"},
            ]
        )
        self.assertEqual(self.execute(f)["status"], "abstained")

    def test_abstention_has_no_repair(self):
        f = Fake(
            [
                {"query": "unavailable", "complex": False},
                {"abstain": True, "claims": []},
            ]
        )
        self.assertEqual(self.execute(f)["repairs"], 0)

    def test_failure_closed(self):
        self.assertEqual(self.execute(Fake([]))["status"], "error")

    def test_session_scope_and_forget(self):
        self.m.save("a", "q", {"claims": []}, "approved")
        self.m.save("b", "x", {}, "approved")
        self.m.save("a", "bad", {}, "abstained")
        self.assertEqual(len(self.m.recall("a")), 1)
        self.m.forget("a")
        self.assertEqual(self.m.recall("a"), [])
        self.assertEqual(len(self.m.recall("b")), 1)

    def test_input_limits(self):
        for q in ["", "x" * 2001]:
            with self.assertRaises(ValueError):
                self.execute(Fake([]), q)

    def test_history_date_scope(self):
        self.m.save("a", "old", {"as_of": "2026-08-31"}, "approved")
        self.m.save("a", "current", {"as_of": "2026-11-10"}, "approved")
        self.assertEqual(
            [r["question"] for r in self.m.recall("a", "2026-08-31")], ["old"]
        )

    def test_reingest_removes_deleted_sections(self):
        d = Path(self.tmp.name) / "docs"
        d.mkdir()
        self.m.ingest(d)
        self.assertEqual(self.m.search_documents("backup", "2026-11-10"), [])

    def test_telemetry_alerts_and_traces(self):
        with self.t.span("unit"):
            self.t.inc("requests_total")
        self.t.alert("test_only")
        self.assertTrue((self.t.root / "metrics.prom").exists())
        self.assertTrue((self.t.root / "alerts.jsonl").exists())


if __name__ == "__main__":
    unittest.main()
