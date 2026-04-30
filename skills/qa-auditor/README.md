# QA Auditor Skill

This skill provides expertise in code review and API auditing to ensure Zero-Backend-LLM compliance in Phase 1. Responsible for verifying that no forbidden LLM API calls, RAG summarization, or agent loops exist in the backend.

## Components

### SKILL.md
Core instructions and patterns for Zero-Backend-LLM compliance with focus on:
- Code review techniques for LLM integration detection
- API auditing for compliance verification
- Static and dynamic analysis methods
- Remediation strategies for violations
- Compliance reporting and validation

### References
- `auditing-techniques.md` - Comprehensive guide for LLM integration detection using static and dynamic analysis
- `remediation-strategies.md` - Detailed strategies for replacing LLM-dependent code with compliant alternatives

### Scripts
- `audit_backend.py` - Comprehensive tool for auditing codebases for LLM integration violations
- `remediate_violations.py` - Automated tool for fixing common LLM integration violations

### Assets
- `remediation-templates.md` - Ready-to-use templates for common violation patterns and fixes

## Usage

Use this skill when performing:
- Code reviews to identify LLM integration violations
- API audits for Zero-Backend-LLM compliance
- Security assessments of backend systems
- Verification of deterministic backend operations
- Compliance checks for educational technology systems
- Pre-deployment validation of backend logic

## Quick Start

### For Backend Auditing:
```bash
python scripts/audit_backend.py /path/to/codebase --format json --output audit_report.json
```

### For Violation Remediation:
```bash
python scripts/remediate_violations.py /path/to/codebase --dry-run
python scripts/remediate_violations.py /path/to/codebase --backup
```

### For Single File Audit:
```bash
python scripts/audit_backend.py /path/to/file.py
```