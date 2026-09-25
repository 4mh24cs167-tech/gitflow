import hashlib
import hmac
import os
import unittest
from unittest.mock import patch
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from sqlalchemy import select, update

from app.api.routes.webhooks import verify_signature
from app.scanners.universal import generate_fingerprint
from app.scoring.engine import calculate_risk_score
from app.workers.scan_job import calculate_score_delta, previous_completed_score
from app.api.routes.repositories import get_risk_history
from app.database.models import Commit, Repository, RiskScore, Scan, User
from app.database.session import AsyncSessionLocal


class SecurityCoreTests(unittest.TestCase):
    def test_webhook_signature_rejects_tampering(self):
        body = b'{"after":"a"}'
        signature = "sha256=" + hmac.new(b"secret", body, hashlib.sha256).hexdigest()
        self.assertTrue(verify_signature(body, signature, "secret"))
        self.assertFalse(verify_signature(body + b" ", signature, "secret"))

    def test_fingerprint_is_not_commit_dependent(self):
        one = generate_fingerprint("rule", "src/a.py", "Line 2", "safe description")
        two = generate_fingerprint("rule", "src/a.py", "Line 2", "safe description")
        self.assertEqual(one, two)

    def test_score_is_bounded_and_deduplicated(self):
        finding = {"fingerprint": "same", "category": "Secret", "severity": "Critical", "message": "Potential secret found."}
        result = calculate_risk_score([finding] * 10)
        self.assertEqual(result["final_score"], 75)
        self.assertEqual(len(result["deductions"]), 1)

    def test_worker_environment_inherits_network_settings(self):
        # Regression guard for proxy/DNS configuration required by Git transport.
        inherited = {"PATH": "test-path", "HTTPS_PROXY": "http://proxy.invalid"}
        with patch.dict(os.environ, inherited, clear=True):
            environment = os.environ.copy()
            environment.update({"GIT_TERMINAL_PROMPT": "0", "GIT_ASKPASS": "temporary-helper", "GITHUB_OAUTH_TOKEN": "in-memory-only"})
        self.assertEqual(environment["HTTPS_PROXY"], "http://proxy.invalid")
        self.assertEqual(environment["GIT_TERMINAL_PROMPT"], "0")
        self.assertNotIn("in-memory-only", "https://github.com/example/repo.git")

    def test_score_delta_math(self):
        self.assertIsNone(calculate_score_delta(80, None))
        self.assertEqual(calculate_score_delta(90, 80), 10)
        self.assertEqual(calculate_score_delta(70, 90), -20)
        self.assertEqual(calculate_score_delta(70, 70), 0)


class RiskHistoryDeltaIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.now = datetime.now(timezone.utc)
        suffix = uuid4().hex
        async with AsyncSessionLocal() as db:
            self.user = User(username=f"delta-{suffix}", email=f"delta-{suffix}@example.invalid", hashed_password="test")
            db.add(self.user); await db.flush()
            self.repo = Repository(name="delta-test", url=f"https://github.com/example/delta-{suffix}.git", owner_id=self.user.id)
            db.add(self.repo); await db.flush()
            self.repo_id, self.user_id = self.repo.id, self.user.id

            def add_scan(offset, status, score=None, delta=None):
                commit = Commit(repository_id=self.repo_id, hash=(f"{offset:02x}" * 20), message="delta test")
                db.add(commit); awaitable = None
                return commit, status, score, delta, offset

            records = []
            for offset, status, score, delta in [(1, "COMPLETED", 80, None), (2, "FAILED", None, None), (3, "COMPLETED", 90, 10), (4, "COMPLETED", 70, -20), (5, "COMPLETED", 70, 0)]:
                commit = Commit(repository_id=self.repo_id, hash=(f"{offset:02x}" * 20), message="delta test")
                db.add(commit); await db.flush()
                scan = Scan(commit_id=commit.id, status=status, completed_at=self.now + timedelta(seconds=offset))
                db.add(scan); await db.flush()
                if score is not None: db.add(RiskScore(scan_id=scan.id, score=score, score_delta=delta, details="{}"))
                records.append(scan)
            await db.commit()
            self.scans = records

    async def test_failed_scan_is_not_baseline_and_api_returns_persisted_deltas(self):
        async with AsyncSessionLocal() as db:
            # Scan 3 is represented as running during score calculation: the prior
            # FAILED scan must be ignored and scan 1's score selected instead.
            # Later scans cannot be a baseline for scan 3 while it is running.
            await db.execute(update(Scan).where(Scan.id.in_([scan.id for scan in self.scans[2:]])).values(status="QUEUED", completed_at=None))
            await db.commit()
            self.assertEqual(await previous_completed_score(db, self.repo_id, self.scans[2].id), 80)
            for index, scan in enumerate(self.scans[2:], start=3):
                await db.execute(update(Scan).where(Scan.id == scan.id).values(status="COMPLETED", completed_at=self.now + timedelta(seconds=index)))
            await db.commit()
            user = (await db.execute(select(User).where(User.id == self.user_id))).scalars().one()
            history = await get_risk_history(self.repo_id, user, db)
        self.assertEqual([entry["risk_score"] for entry in history], [80, 90, 70, 70])
        self.assertEqual([entry["score_delta"] for entry in history], [None, 10, -20, 0])
