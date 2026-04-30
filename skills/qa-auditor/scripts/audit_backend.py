#!/usr/bin/env python3
"""
Zero-Backend-LLM Compliance Auditor
Comprehensive tool for auditing codebases for LLM integration violations
"""

import os
import sys
import re
import ast
import json
import argparse
from pathlib import Path
from typing import List, Dict, Set
from datetime import datetime

class LLMViolationDetector(ast.NodeVisitor):
    """
    AST-based detector for LLM API calls and patterns
    """
    def __init__(self):
        self.violations = []
        self.imports = set()
        self.llm_indicators = {
            'packages': [
                'openai', 'anthropic', 'cohere', 'transformers', 'huggingface_hub',
                'langchain', 'llama_index', 'crewai', 'autogen',
                'pinecone', 'weaviate', 'chromadb', 'faiss', 'qdrant',
                'ollama', 'llama_cpp', 'vllm', 'text_generation'
            ],
            'functions': [
                'create', 'generate', 'complete', 'embed', 'call',
                'chat', 'completions', 'messages', 'generate_text'
            ],
            'classes': [
                'Client', 'API', 'Model', 'Completion', 'Embedding',
                'LLM', 'Chat', 'Pipeline', 'Agent'
            ],
            'methods': [
                'chat', 'completions', 'messages', 'generate',
                'embed', 'call', 'predict', 'invoke'
            ]
        }

    def visit_Import(self, node):
        for alias in node.names:
            self.imports.add(alias.name.lower())

            # Check if import matches LLM packages
            for llm_pkg in self.llm_indicators['packages']:
                if llm_pkg in alias.name.lower():
                    self.violations.append({
                        'type': 'import_violation',
                        'line': node.lineno,
                        'code': f"import {alias.name}",
                        'severity': 'critical',
                        'message': f"LLM package import detected: {alias.name}",
                        'pattern': llm_pkg
                    })
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        for llm_pkg in self.llm_indicators['packages']:
            if llm_pkg in node.module.lower():
                self.violations.append({
                    'type': 'import_violation',
                    'line': node.lineno,
                    'code': f"from {node.module} import ...",
                    'severity': 'critical',
                    'message': f"Import from LLM package: {node.module}",
                    'pattern': llm_pkg
                })

        # Check imported names for LLM patterns
        for alias in node.names:
            name_lower = alias.name.lower()
            for llm_cls in self.llm_indicators['classes']:
                if llm_cls.lower() in name_lower:
                    self.violations.append({
                        'type': 'class_import_violation',
                        'line': node.lineno,
                        'code': f"from {node.module} import {alias.name}",
                        'severity': 'high',
                        'message': f"Imported LLM-related class: {alias.name}",
                        'pattern': llm_cls
                    })
        self.generic_visit(node)

    def visit_Call(self, node):
        # Check function calls for LLM patterns
        if isinstance(node.func, ast.Attribute):
            # Check method calls like client.chat.completions.create()
            method_chain = self._get_attribute_chain(node.func)

            # Check for LLM API call patterns
            if self._is_llm_api_call(method_chain):
                self.violations.append({
                    'type': 'api_call_violation',
                    'line': node.lineno,
                    'code': ast.unparse(node),
                    'severity': 'critical',
                    'message': f"Potential LLM API call: {'.'.join(method_chain)}",
                    'pattern': '.'.join(method_chain)
                })

        elif isinstance(node.func, ast.Name):
            # Check direct function calls
            func_name = node.func.id.lower()
            for llm_func in self.llm_indicators['functions']:
                if llm_func in func_name:
                    self.violations.append({
                        'type': 'function_call_violation',
                        'line': node.lineno,
                        'code': ast.unparse(node),
                        'severity': 'high',
                        'message': f"Potential LLM function call: {func_name}",
                        'pattern': llm_func
                    })
        self.generic_visit(node)

    def _get_attribute_chain(self, node) -> List[str]:
        """Extract attribute chain like ['client', 'chat', 'completions', 'create']"""
        chain = []
        current = node
        while isinstance(current, ast.Attribute):
            chain.insert(0, current.attr.lower())
            current = current.value

        if isinstance(current, ast.Name):
            chain.insert(0, current.id.lower())

        return chain

    def _is_llm_api_call(self, chain: List[str]) -> bool:
        """Check if attribute chain suggests LLM API usage"""
        # Common LLM API patterns
        llm_patterns = [
            ['openai', 'chat', 'completions', 'create'],
            ['client', 'chat', 'completions', 'create'],
            ['anthropic', 'messages', 'create'],
            ['client', 'messages', 'create'],
            ['openai', 'embeddings', 'create'],
            ['cohere', 'embed'],
            ['transformers', 'pipeline'],
            ['langchain', 'llm', 'call'],
            ['llm', 'generate'],
            ['chat', 'invoke']
        ]

        chain_lower = [part for part in chain]

        for pattern in llm_patterns:
            if len(chain) >= len(pattern):
                for i in range(len(chain) - len(pattern) + 1):
                    if chain_lower[i:i+len(pattern)] == pattern:
                        return True

        return False

class FileScanner:
    """
    Scans files for LLM-related patterns using various techniques
    """
    def __init__(self):
        self.forbidden_patterns = [
            # LLM API clients
            r'import openai',
            r'from openai import',
            r'import anthropic',
            r'from anthropic import',
            r'import cohere',
            r'from cohere import',
            r'import transformers',
            r'from transformers import',
            r'import huggingface_hub',
            r'from huggingface_hub import',

            # LLM API calls
            r'openai\.(ChatCompletion|Completion)\.create',
            r'client\.(chat|completions|messages)\.create',
            r'anthropic\.',
            r'cohere\.',
            r'transformers\.pipeline',
            r'huggingface_hub\.snapshot_download',

            # Agent frameworks
            r'import langchain',
            r'from langchain import',
            r'import llama_index',
            r'from llama_index import',
            r'import (crewai|autogen|autonomous_agents)',
            r'from (crewai|autogen|autonomous_agents) import',

            # Vector databases
            r'import (pinecone|weaviate|chromadb|faiss|qdrant)',
            r'(pinecone|weaviate|chromadb|faiss|qdrant)\.',

            # Embedding services
            r'openai\.Embedding',
            r'client\.embeddings',
            r'cohere\.embed',
            r'sentence_transformers\.',
            r'chromadb\.EmbeddingFunction'
        ]

        self.llm_packages = {
            'openai', 'anthropic', 'cohere', 'transformers', 'huggingface_hub',
            'langchain', 'llama-index', 'crewai', 'autogen',
            'pinecone-client', 'weaviate-client', 'chromadb', 'faiss-cpu',
            'sentence-transformers', 'instructor', 'guidance', 'llm',
            'gpt', 'ai', 'ml', 'machine-learning', 'vectorstores'
        }

    def scan_python_file(self, file_path: str) -> List[Dict]:
        """Scan a Python file for LLM violations"""
        violations = []

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # AST-based scanning
            try:
                tree = ast.parse(content)
                detector = LLMViolationDetector()
                detector.visit(tree)
                violations.extend(detector.violations)
            except SyntaxError:
                violations.append({
                    'type': 'syntax_error',
                    'file': file_path,
                    'severity': 'medium',
                    'message': 'Syntax error in file'
                })

            # Regex-based scanning
            for i, pattern in enumerate(self.forbidden_patterns):
                if re.search(pattern, content, re.IGNORECASE):
                    violations.append({
                        'type': 'regex_violation',
                        'file': file_path,
                        'pattern': pattern,
                        'severity': 'critical' if i < 10 else 'high',
                        'message': f"Regex pattern matched: {pattern}"
                    })

        except Exception as e:
            violations.append({
                'type': 'scan_error',
                'file': file_path,
                'error': str(e),
                'severity': 'medium',
                'message': f"Could not scan file: {str(e)}"
            })

        return violations

    def scan_requirements_file(self, file_path: str) -> List[Dict]:
        """Scan requirements.txt for LLM packages"""
        violations = []

        try:
            with open(file_path, 'r') as f:
                lines = f.readlines()

            for line_num, line in enumerate(lines, 1):
                line_clean = line.split('#')[0].strip()  # Remove comments
                if line_clean:
                    # Extract package name (handles version specs)
                    package_name = re.split(r'[>=<!=~]', line_clean)[0].strip().lower()

                    if package_name in self.llm_packages:
                        violations.append({
                            'type': 'dependency_violation',
                            'file': file_path,
                            'line': line_num,
                            'package': package_name,
                            'severity': 'critical',
                            'message': f"LLM dependency in requirements: {package_name}"
                        })

        except Exception as e:
            violations.append({
                'type': 'scan_error',
                'file': file_path,
                'error': str(e),
                'severity': 'medium',
                'message': f"Could not scan requirements: {str(e)}"
            })

        return violations

    def scan_directory(self, directory: str, include_tests: bool = False) -> List[Dict]:
        """Scan an entire directory for LLM violations"""
        violations = []

        for root, dirs, files in os.walk(directory):
            # Skip common directories that shouldn't contain backend code
            dirs[:] = [d for d in dirs if d not in ['.git', 'node_modules', '__pycache__', '.venv', 'venv', 'env']]

            # Skip test directories unless explicitly included
            if not include_tests and any(part in root.lower() for part in ['test', 'tests', 'spec']):
                continue

            for file in files:
                file_path = os.path.join(root, file)

                if file.endswith('.py'):
                    violations.extend(self.scan_python_file(file_path))

                elif file.lower() in ['requirements.txt', 'requirements-dev.txt', 'requirements-test.txt']:
                    violations.extend(self.scan_requirements_file(file_path))

        return violations

def calculate_severity_score(violations: List[Dict]) -> float:
    """Calculate overall severity score based on violations"""
    if not violations:
        return 0.0

    severity_weights = {'critical': 10, 'high': 5, 'medium': 2, 'low': 1}
    total_score = sum(severity_weights.get(v.get('severity', 'medium'), 2) for v in violations)

    # Normalize based on number of violations
    return min(total_score / len(violations) if violations else 0, 10.0)

def generate_report(violations: List[Dict], output_format: str = 'text') -> str:
    """Generate audit report in specified format"""
    if output_format == 'json':
        return json.dumps({
            'timestamp': datetime.now().isoformat(),
            'total_violations': len(violations),
            'violations': violations,
            'severity_score': calculate_severity_score(violations),
            'compliant': len([v for v in violations if v['severity'] in ['critical', 'high']]) == 0
        }, indent=2)

    # Text format
    report = f"""
Zero-Backend-LLM Compliance Audit Report
========================================

Timestamp: {datetime.now().isoformat()}
Total Violations Found: {len(violations)}

Severity Breakdown:
"""

    severity_counts = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
    for v in violations:
        severity = v.get('severity', 'medium')
        if severity in severity_counts:
            severity_counts[severity] += 1

    for severity, count in severity_counts.items():
        report += f"  {severity.upper()}: {count}\n"

    report += f"\nOverall Severity Score: {calculate_severity_score(violations):.2f}/10.0\n"
    report += f"Compliant: {'YES' if severity_counts['critical'] == 0 and severity_counts['high'] == 0 else 'NO'}\n\n"

    if violations:
        report += "Violations Found:\n"
        report += "-" * 50 + "\n"

        for i, violation in enumerate(violations[:20], 1):  # Show first 20 violations
            report += f"{i}. SEVERITY: {violation.get('severity', 'unknown').upper()}\n"
            report += f"   TYPE: {violation.get('type', 'unknown')}\n"
            report += f"   FILE: {violation.get('file', 'unknown')}\n"
            report += f"   LINE: {violation.get('line', 'N/A')}\n"
            report += f"   MESSAGE: {violation.get('message', 'No message')}\n"
            report += f"   CODE: {violation.get('code', 'N/A')}\n\n"

        if len(violations) > 20:
            report += f"... and {len(violations) - 20} more violations\n\n"

    report += "Recommendations:\n"
    report += "-" * 15 + "\n"
    if severity_counts['critical'] > 0:
        report += "• CRITICAL: Address all LLM API calls immediately\n"
    if severity_counts['high'] > 0:
        report += "• HIGH: Remove all LLM dependencies and agent frameworks\n"
    if severity_counts['medium'] > 0:
        report += "• MEDIUM: Review configuration files for LLM settings\n"
    if severity_counts['low'] > 0:
        report += "• LOW: Clean up any remaining LLM-related code\n"

    return report

def main():
    parser = argparse.ArgumentParser(description='Zero-Backend-LLM Compliance Auditor')
    parser.add_argument('path', help='Path to directory or file to audit')
    parser.add_argument('--format', choices=['text', 'json'], default='text',
                       help='Output format (default: text)')
    parser.add_argument('--include-tests', action='store_true',
                       help='Include test files in scan')
    parser.add_argument('--output', help='Output file path')

    args = parser.parse_args()

    print("🔍 Starting Zero-Backend-LLM compliance audit...")
    print(f"📁 Scanning: {args.path}")
    print(f"📝 Format: {args.format}")
    print()

    scanner = FileScanner()

    path = Path(args.path)
    if path.is_file():
        # Scan single file
        if path.suffix == '.py':
            violations = scanner.scan_python_file(str(path))
        elif path.name.lower() in ['requirements.txt', 'requirements-dev.txt', 'requirements-test.txt']:
            violations = scanner.scan_requirements_file(str(path))
        else:
            print(f"❌ Unsupported file type: {path.suffix}")
            sys.exit(1)
    else:
        # Scan directory
        violations = scanner.scan_directory(
            str(path),
            include_tests=args.include_tests
        )

    # Generate report
    report = generate_report(violations, args.format)

    # Output results
    if args.output:
        with open(args.output, 'w') as f:
            f.write(report)
        print(f"📊 Report saved to: {args.output}")
    else:
        print(report)

    # Exit with error code if violations found
    critical_high_violations = [v for v in violations if v['severity'] in ['critical', 'high']]
    if critical_high_violations:
        print(f"❌ Audit FAILED: {len(critical_high_violations)} critical/high violations found")
        sys.exit(1)
    else:
        print("✅ Audit PASSED: No critical or high severity violations found")
        sys.exit(0)

if __name__ == "__main__":
    main()