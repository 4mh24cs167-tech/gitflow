import re
import os
import hashlib
from typing import List, Dict, Any

# Basic Secret Patterns (Deterministic)
SECRET_PATTERNS = {
    "AWS Access Key": r"(?i)AKIA[0-9A-Z]{16}",
    "Generic API Key or Token": r"(?i)(?:key|token|secret|password)[_-]?\s*[:=]\s*['\"]?([0-9a-zA-Z\-_]{16,})['\"]?",
    "Private Key": r"-----BEGIN (?:RSA|OPENSSH|DSA|EC|PGP) PRIVATE KEY-----"
}

# Suspicious file extensions
SUSPICIOUS_EXTENSIONS = {".p12", ".pem", ".key", ".pkcs12", ".pfx"}
SKIP_DIRECTORIES = {".git", "node_modules", "venv", ".venv", "dist", "build", "target", "vendor", "__pycache__"}
MAX_FILE_BYTES = 512 * 1024

# Allowed licenses for MVP
ALLOWED_LICENSES = {"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause"}

def generate_fingerprint(rule: str, file_path: str, location: str, message: str) -> str:
    fingerprint_string = f"{rule}:{file_path}:{location}:{message}"
    return hashlib.sha256(fingerprint_string.encode('utf-8')).hexdigest()

class UniversalScanner:
    def __init__(self, repo_path: str):
        self.repo_path = repo_path
        self.findings = []
        
    def scan(self) -> List[Dict[str, Any]]:
        self.findings = []
        self._analyze_files()
        self._analyze_license()
        self._analyze_dependencies()
        return self.findings
        
    def _add_finding(self, rule: str, file_path: str, location: str, message: str, severity: str, category: str):
        fingerprint = generate_fingerprint(rule, file_path, location, message)
        self.findings.append({
            "fingerprint": fingerprint,
            "rule": rule,
            "file_path": file_path,
            "location": location,
            "message": message,
            "severity": severity,
            "category": category
        })
        
    def _analyze_files(self):
        for root, dirs, files in os.walk(self.repo_path):
            dirs[:] = [directory for directory in dirs if directory not in SKIP_DIRECTORIES]
                
            for file_name in files:
                file_path = os.path.join(root, file_name)
                rel_path = os.path.relpath(file_path, self.repo_path)
                
                if not os.path.isfile(file_path):
                    continue
                # Check extension
                ext = os.path.splitext(file_name)[1].lower()
                if ext in SUSPICIOUS_EXTENSIONS:
                    self._add_finding(
                        rule="Suspicious Extension",
                        file_path=rel_path,
                        location="File",
                        message=f"File extension {ext} may indicate sensitive key material.",
                        severity="High",
                        category="Secret"
                    )
                
                # Large file check (e.g. > 1MB)
                try:
                    size = os.path.getsize(file_path)
                    if size > 1024 * 1024:
                        self._add_finding(
                            rule="Large File",
                            file_path=rel_path,
                            location="File",
                            message="File is larger than 1MB, which may affect performance.",
                            severity="Low",
                            category="Quality"
                        )
                except OSError:
                    continue

                # Read content for secrets and code quality (skip binary looking files based on size/extension)
                if size < MAX_FILE_BYTES and ext not in {'.png', '.jpg', '.jpeg', '.pdf', '.zip', '.tar', '.gz', '.exe', '.dll'}:
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            lines = f.readlines()
                            
                            # Proxy for high complexity / duplication: extremely long files
                            if len(lines) > 1000:
                                self._add_finding(
                                    rule="High Complexity",
                                    file_path=rel_path,
                                    location="File",
                                    message="File exceeds 1,000 lines, indicating potential high complexity or duplicate code.",
                                    severity="Medium",
                                    category="Quality"
                                )
                                
                            for idx, line in enumerate(lines):
                                for pattern_name, pattern in SECRET_PATTERNS.items():
                                    if re.search(pattern, line):
                                        self._add_finding(
                                            rule=f"Secret Detection: {pattern_name}",
                                            file_path=rel_path,
                                            location=f"Line {idx + 1}",
                                            message=f"Potential {pattern_name} found.",
                                            severity="Critical",
                                            category="Secret"
                                        )
                    except UnicodeDecodeError:
                        pass # Likely binary
                        
    def _analyze_dependencies(self):
        import subprocess
        import json
        
        # Check if osv-scanner is available
        try:
            subprocess.run(["osv-scanner", "--version"], capture_output=True, check=True, timeout=10)
            has_osv = True
        except (subprocess.CalledProcessError, FileNotFoundError):
            has_osv = False
            
        if has_osv:
            try:
                result = subprocess.run(
                    ["osv-scanner", "-r", "--json", self.repo_path],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    check=True,
                )
                if result.stdout:
                    data = json.loads(result.stdout)
                    results = data.get("results", [])
                    for res in results:
                        source = res.get("source", {}).get("path", "")
                        rel_path = os.path.relpath(source, self.repo_path)
                        packages = res.get("packages", [])
                        for pkg in packages:
                            vulns = pkg.get("vulnerabilities", [])
                            for vuln in vulns:
                                self._add_finding(
                                    rule="Dependency Vulnerability",
                                    file_path=rel_path,
                                    location="Package Manifest",
                                    message=f"Vulnerability {vuln.get('id')} found in {pkg.get('package', {}).get('name')}",
                                    severity="High", # Can map severity properly based on CVSS later
                                    category="Vulnerability"
                                )
            except Exception:
                self._add_finding("Dependency Scan Unavailable", "Repository", "Root", "Dependency scan could not be completed; vulnerability results are unavailable.", "Informational", "DependencyScan")
        else:
            self._add_finding("Dependency Scan Unavailable", "Repository", "Root", "OSV-Scanner is not installed; vulnerability results are unavailable.", "Informational", "DependencyScan")
                        
    def _analyze_license(self):
        # Look for LICENSE file
        license_path = next((os.path.join(self.repo_path, name) for name in ('LICENSE', 'LICENSE.txt', 'LICENSE.md') if os.path.exists(os.path.join(self.repo_path, name))), None)
             
        if not license_path:
            self._add_finding(
                rule="Missing License",
                file_path="Repository",
                location="Root",
                message="No LICENSE or LICENSE.md file found in repository root.",
                severity="Medium",
                category="License"
            )
        else:
            try:
                with open(license_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if "MIT" in content:
                        pass # Acceptable
                    elif "Apache License" in content and "2.0" in content:
                        pass # Acceptable
                    else:
                        self._add_finding(
                            rule="Unknown/Custom License",
                            file_path=os.path.basename(license_path),
                            location="Root",
                            message="License file detected but could not be definitively categorized as a standard permissive license.",
                            severity="Low",
                            category="License"
                        )
            except Exception:
                pass
