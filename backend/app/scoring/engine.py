from enum import Enum
from typing import List, Dict, Any

class Severity(str, Enum):
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    INFORMATIONAL = "Informational"

DEDUCTIONS = {
    "VULNERABILITY": {
        Severity.CRITICAL: 25,
        Severity.HIGH: 15,
        Severity.MEDIUM: 8,
        Severity.LOW: 3,
    },
    "SECRET": {
        Severity.CRITICAL: 25,
        Severity.HIGH: 25,
    },
    "LICENSE": {
        Severity.HIGH: 15,
        Severity.MEDIUM: 10,
    },
    "QUALITY": {
        Severity.HIGH: 10,
        Severity.MEDIUM: 5,
        Severity.LOW: 2,
    },
    "ARCHITECTURE": {
        Severity.HIGH: 10,
        Severity.MEDIUM: 5,
    }
}

def calculate_risk_score(findings: List[Dict[str, Any]]) -> Dict[str, Any]:
    score = 100
    deductions = []
    # A scanner must not be able to reduce a score repeatedly by emitting an
    # identical finding more than once.
    unique_findings = {f.get("fingerprint") or repr(sorted(f.items())): f for f in findings}
    for finding in unique_findings.values():
        category = finding.get("category", "Vulnerability").upper()
        severity_str = finding.get("severity", "Medium")
        
        try:
            severity = Severity(severity_str.capitalize())
        except ValueError:
            severity = Severity.MEDIUM
                
        category_deductions = DEDUCTIONS.get(category, DEDUCTIONS["VULNERABILITY"])
        
        deduction = category_deductions.get(severity, 0)
        
        # Fallback if specific category doesn't define the severity
        if deduction == 0:
            if severity == Severity.CRITICAL:
                deduction = 25
            elif severity == Severity.HIGH:
                deduction = 15
            elif severity == Severity.MEDIUM:
                deduction = 8
            elif severity == Severity.LOW:
                deduction = 3
                
        score -= deduction
        deductions.append({
            "category": category.lower(),
            "severity": severity.value,
            "description": finding.get("message", "Finding"),
            "points": -deduction,
            "fingerprint": finding.get("fingerprint", "")
        })
        
    return {
        "base_score": 100,
        "final_score": max(0, min(100, score)),
        "deductions": deductions
    }
