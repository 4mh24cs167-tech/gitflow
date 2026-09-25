import json
import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import select
from app.auth.security import decrypt_token
from app.config import settings
from app.database.models import Commit, Finding, Repository, RiskScore, Scan, User
from app.database.session import AsyncSessionLocal
from app.scanners.universal import UniversalScanner
from app.scoring.engine import calculate_risk_score

def safe_error(exc: Exception) -> str:
    """Keep operational errors useful without returning paths, URLs, or credentials."""
    if isinstance(exc, subprocess.TimeoutExpired): return "Git operation timed out"
    if isinstance(exc, subprocess.CalledProcessError): return "Git could not retrieve the requested commit"
    return "Scan failed while analyzing the repository"

def calculate_score_delta(current_score: int, previous_score: int | None) -> int | None:
    """Return a persisted history delta; the first completed scan has no baseline."""
    return None if previous_score is None else current_score - previous_score

async def previous_completed_score(db, repository_id: int, current_scan_id: int) -> int | None:
    """Return only the score for the immediately preceding completed scan."""
    previous = (await db.execute(
        select(Scan).join(Scan.commit)
        .where(Commit.repository_id == repository_id, Scan.status == "COMPLETED", Scan.id != current_scan_id)
        .order_by(Scan.completed_at.desc()).limit(1)
    )).scalars().first()
    if not previous:
        return None
    score = (await db.execute(select(RiskScore).where(RiskScore.scan_id == previous.id))).scalars().first()
    return score.score if score else None

async def run_scan(scan_id: int):
    temp_dir = None
    askpass_path = None
    async with AsyncSessionLocal() as db:
        scan = (await db.execute(select(Scan).where(Scan.id == scan_id))).scalars().first()
        if not scan or scan.status != "QUEUED": return
        scan.status = "RUNNING"; await db.commit()
        try:
            scan = (await db.execute(select(Scan).where(Scan.id == scan_id))).scalars().one()
            commit = (await db.execute(select(Commit).where(Commit.id == scan.commit_id))).scalars().one()
            repo = (await db.execute(select(Repository).where(Repository.id == commit.repository_id))).scalars().one()
            user = (await db.execute(select(User).where(User.id == repo.owner_id))).scalars().one()
            oauth_token = decrypt_token(user.github_access_token or "")
            if not oauth_token:
                raise RuntimeError("GitHub authentication is required to scan this repository")
            temp_dir = tempfile.mkdtemp(prefix="risk_passport_scan_")
            # Git requests credentials from this short-lived helper. The token exists
            # only in this child process environment; it is never in a URL, command
            # line, or repository configuration file.
            helper = tempfile.NamedTemporaryFile(mode="w", suffix=".cmd", prefix="risk_passport_askpass_", delete=False, encoding="utf-8")
            helper.write("@echo off\r\n")
            helper.write("echo %~1 | findstr /i /c:\"username\" >nul\r\n")
            helper.write("if not errorlevel 1 (echo x-access-token) else (echo %GITHUB_OAUTH_TOKEN%)\r\n")
            helper.close()
            askpass_path = helper.name
            # Preserve host networking/proxy configuration while overriding only
            # Git controls needed for non-interactive, in-memory authentication.
            env = os.environ.copy()
            env.update({"GIT_TERMINAL_PROMPT": "0", "GIT_CONFIG_NOSYSTEM": "1", "GIT_ASKPASS": askpass_path, "GIT_ASKPASS_REQUIRE": "force", "GITHUB_OAUTH_TOKEN": oauth_token})
            # Do not use --depth: an older webhook commit must remain fetchable after
            # newer commits reach the branch. --no-checkout prevents hooks/scripts.
            subprocess.run(["git", "clone", "--no-checkout", repo.url, temp_dir], check=True, capture_output=True, text=True, timeout=settings.SCAN_TIMEOUT_SECONDS, env=env)
            del oauth_token
            env.pop("GITHUB_OAUTH_TOKEN", None)
            env.pop("GIT_ASKPASS", None)
            subprocess.run(["git", "-C", temp_dir, "checkout", "--detach", commit.hash], check=True, capture_output=True, text=True, timeout=settings.SCAN_TIMEOUT_SECONDS, env=env)
            checked_out = subprocess.run(["git", "-C", temp_dir, "rev-parse", "HEAD"], check=True, capture_output=True, text=True, timeout=10, env=env).stdout.strip().lower()
            if checked_out != commit.hash: raise RuntimeError("checked out revision did not match requested SHA")
            
            # 1. Standard Universal Scan
            raw_findings = UniversalScanner(temp_dir).scan()
            
            # 2. Structural & Impact Analysis
            from app.analysis.impact import analyze_commit_changes, analyze_structural_changes, build_dependency_graph, analyze_impact
            from app.database.models import CommitAnalysis
            
            changed_files_data = analyze_commit_changes(temp_dir, commit.hash)
            structural_changes_data = analyze_structural_changes(temp_dir, commit.hash)
            dep_graph = build_dependency_graph(temp_dir)
            changed_file_paths = [cf['file_path'] for cf in changed_files_data if cf['status'] in ('ADDED', 'MODIFIED', 'RENAMED')]
            impact_data = analyze_impact(changed_file_paths, dep_graph)
            
            db.add(CommitAnalysis(
                scan_id=scan.id,
                changed_files=json.dumps(changed_files_data),
                structural_changes=json.dumps(structural_changes_data),
                dependency_graph=json.dumps(dep_graph),
                impact_analysis=json.dumps(impact_data)
            ))
            
            # 3. Calculate Risk
            score_breakdown = calculate_risk_score(raw_findings)
            # You could inject impact_data into risk score calculation here if desired.
            
            previous = (await db.execute(select(Scan).join(Scan.commit).where(Commit.repository_id == repo.id, Scan.status == "COMPLETED", Scan.id != scan.id).order_by(Scan.completed_at.desc()).limit(1))).scalars().first()
            previous_score = await previous_completed_score(db, repo.id, scan.id)
            previous_findings = [] if not previous else list((await db.execute(select(Finding).where(Finding.scan_id == previous.id, Finding.status != "RESOLVED"))).scalars())
            previous_by_fingerprint = {f.fingerprint: f for f in previous_findings}
            current = {f["fingerprint"]: f for f in raw_findings}
            for fingerprint, finding in current.items():
                db.add(Finding(scan_id=scan.id, fingerprint=fingerprint, status="UNCHANGED" if fingerprint in previous_by_fingerprint else "NEW", type=finding["category"], description=finding["message"], file_path=finding["file_path"], severity=finding["severity"]))
            for fingerprint, finding in previous_by_fingerprint.items():
                if fingerprint not in current:
                    db.add(Finding(scan_id=scan.id, fingerprint=fingerprint, status="RESOLVED", type=finding.type, description=finding.description, file_path=finding.file_path, line_number=finding.line_number, severity=finding.severity))
            db.add(RiskScore(scan_id=scan.id, score=score_breakdown["final_score"], score_delta=calculate_score_delta(score_breakdown["final_score"], previous_score), details=json.dumps(score_breakdown)))
            scan.status = "COMPLETED"; scan.completed_at = datetime.utcnow(); scan.error_message = None
        except Exception as exc:
            scan.status = "FAILED"; scan.completed_at = datetime.utcnow(); scan.error_message = safe_error(exc)
        finally:
            if temp_dir: shutil.rmtree(temp_dir, ignore_errors=True)
            if askpass_path:
                try: os.remove(askpass_path)
                except OSError: pass
        await db.commit()
