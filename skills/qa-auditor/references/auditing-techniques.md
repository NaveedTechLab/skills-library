# Zero-Backend-LLM Auditing Techniques

## Static Analysis Methods

### 1. Pattern Matching Approaches

#### Regex-Based Detection
```bash
# Detect common LLM API patterns
grep -r -i -n \
  -E "(openai|anthropic|cohere|transformers|langchain|llama_index|pinecone|weaviate|chromadb|ollama)" \
  --include="*.py" --include="*.js" --include="*.ts" --include="*.go" \
  --include="*.java" --include="*.cpp" --include="*.rb" \
  --exclude-dir=node_modules --exclude-dir=.git \
  . || echo "No LLM patterns found"
```

#### AST-Based Analysis (Python)
```python
import ast
import re
from typing import List, Dict, Set

class LLMCallDetector(ast.NodeVisitor):
    """
    Advanced AST-based detector for LLM API calls
    """
    def __init__(self):
        self.llm_calls = []
        self.imports = set()
        self.variables = {}  # Track variable assignments
        self.llm_indicators = {
            'packages': ['openai', 'anthropic', 'cohere', 'transformers', 'huggingface_hub'],
            'functions': ['create', 'generate', 'complete', 'embed', 'call'],
            'classes': ['Client', 'API', 'Model', 'Completion', 'Embedding'],
            'methods': ['chat', 'completions', 'messages', 'generate']
        }

    def visit_Import(self, node):
        for alias in node.names:
            self.imports.add(alias.name)

            # Check if import matches LLM packages
            for llm_pkg in self.llm_indicators['packages']:
                if llm_pkg in alias.name.lower():
                    self.llm_calls.append({
                        'type': 'import',
                        'line': node.lineno,
                        'code': f"import {alias.name}",
                        'severity': 'high',
                        'message': f"Potential LLM package import: {alias.name}"
                    })
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        for llm_pkg in self.llm_indicators['packages']:
            if llm_pkg in node.module.lower():
                self.llm_calls.append({
                    'type': 'import_from',
                    'line': node.lineno,
                    'code': f"from {node.module} import ...",
                    'severity': 'high',
                    'message': f"Import from potential LLM package: {node.module}"
                })
        self.generic_visit(node)

    def visit_Call(self, node):
        # Check for function calls that might be LLM-related
        if isinstance(node.func, ast.Attribute):
            # Check method calls like client.chat.completions.create()
            method_chain = self._get_attribute_chain(node.func)
            if self._is_llm_method_chain(method_chain):
                self.llm_calls.append({
                    'type': 'method_call',
                    'line': node.lineno,
                    'code': ast.unparse(node),
                    'severity': 'critical',
                    'message': f"Potential LLM API call: {'.'.join(method_chain)}"
                })

        elif isinstance(node.func, ast.Name):
            # Check direct function calls
            func_name = node.func.id
            if self._is_llm_function(func_name):
                self.llm_calls.append({
                    'type': 'function_call',
                    'line': node.lineno,
                    'code': ast.unparse(node),
                    'severity': 'high',
                    'message': f"Potential LLM function call: {func_name}"
                })

        self.generic_visit(node)

    def visit_Assign(self, node):
        # Track variable assignments for context
        if isinstance(node.targets[0], ast.Name):
            var_name = node.targets[0].id
            if isinstance(node.value, ast.Call):
                if isinstance(node.value.func, ast.Name):
                    # Track assignments like client = OpenAI()
                    self.variables[var_name] = ast.unparse(node.value.func)
        self.generic_visit(node)

    def _get_attribute_chain(self, node) -> List[str]:
        """Extract attribute chain like ['client', 'chat', 'completions', 'create']"""
        chain = []
        current = node
        while isinstance(current, ast.Attribute):
            chain.insert(0, current.attr)
            current = current.value

        if isinstance(current, ast.Name):
            chain.insert(0, current.id)

        return chain

    def _is_llm_method_chain(self, chain: List[str]) -> bool:
        """Check if attribute chain suggests LLM usage"""
        # Check for common LLM API patterns
        llm_patterns = [
            ['openai', 'chat', 'completions', 'create'],
            ['client', 'chat', 'completions', 'create'],
            ['anthropic', 'messages', 'create'],
            ['client', 'messages', 'create'],
            ['openai', 'embeddings', 'create'],
            ['cohere', 'embed'],
            ['transformers', 'pipeline']
        ]

        chain_lower = [part.lower() for part in chain]

        for pattern in llm_patterns:
            if len(chain) >= len(pattern):
                for i in range(len(chain) - len(pattern) + 1):
                    if chain_lower[i:i+len(pattern)] == pattern:
                        return True

        return False

    def _is_llm_function(self, func_name: str) -> bool:
        """Check if function name suggests LLM usage"""
        llm_functions = [
            'chatcompletion', 'completion', 'create', 'generate', 'embed',
            'call_llm', 'use_ai', 'ai_generate', 'llm_call'
        ]
        return any(llm_func in func_name.lower() for llm_func in llm_functions)

def scan_file_for_llm_calls(file_path: str) -> List[Dict]:
    """Scan a single Python file for LLM API calls"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        tree = ast.parse(content)
        detector = LLMCallDetector()
        detector.visit(tree)

        return detector.llm_calls
    except Exception as e:
        return [{
            'type': 'scan_error',
            'file': file_path,
            'error': str(e),
            'severity': 'medium',
            'message': f"Could not scan file: {str(e)}"
        }]

def scan_directory_for_llm_calls(directory: str) -> List[Dict]:
    """Scan an entire directory for LLM API calls"""
    import os

    results = []

    for root, dirs, files in os.walk(directory):
        # Skip common directories that shouldn't contain backend code
        dirs[:] = [d for d in dirs if d not in ['.git', 'node_modules', '__pycache__', '.venv', 'venv']]

        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                results.extend(scan_file_for_llm_calls(file_path))

    return results
```

### 2. Dependency Analysis

#### Python Dependency Scanner
```python
import toml
import json
import subprocess
from typing import List, Dict, Set

class DependencyScanner:
    """
    Scan project dependencies for LLM-related packages
    """

    def __init__(self):
        self.llm_packages = {
            # Primary LLM SDKs
            'openai': 'OpenAI API client',
            'anthropic': 'Anthropic API client',
            'cohere': 'Cohere API client',
            'huggingface_hub': 'Hugging Face Hub client',

            # ML/AI Frameworks
            'transformers': 'Transformers library',
            'torch': 'PyTorch (ML framework)',
            'tensorflow': 'TensorFlow (ML framework)',
            'scikit-learn': 'Scikit-learn (ML library)',

            # Agent Frameworks
            'langchain': 'LangChain framework',
            'llama-index': 'LlamaIndex framework',
            'crewai': 'CrewAI framework',
            'autogen': 'AutoGen framework',

            # Vector Databases
            'pinecone-client': 'Pinecone vector database',
            'weaviate': 'Weaviate vector database',
            'chromadb': 'ChromaDB vector database',
            'faiss-cpu': 'FAISS vector database',

            # Embedding Services
            'sentence-transformers': 'Sentence transformers',
            ' InstructorEmbedding': 'Instructor embeddings',

            # API Wrappers
            'openai-api': 'Alternative OpenAI wrapper',
            'anthropic-sdk': 'Alternative Anthropic wrapper',
        }

    def scan_requirements_txt(self, file_path: str) -> List[Dict]:
        """Scan requirements.txt for LLM packages"""
        try:
            with open(file_path, 'r') as f:
                lines = f.readlines()

            violations = []
            for i, line in enumerate(lines, 1):
                line_clean = line.strip().split('#')[0]  # Remove comments
                if line_clean:
                    package_name = line_clean.split('==')[0].split('>=')[0].split('<=')[0].split('>')[0].split('<')[0].strip()

                    if package_name.lower() in self.llm_packages:
                        violations.append({
                            'type': 'dependency_violation',
                            'file': file_path,
                            'line': i,
                            'package': package_name,
                            'description': self.llm_packages[package_name.lower()],
                            'severity': 'critical'
                        })

            return violations
        except FileNotFoundError:
            return []
        except Exception as e:
            return [{
                'type': 'scan_error',
                'file': file_path,
                'error': str(e),
                'severity': 'medium'
            }]

    def scan_pyproject_toml(self, file_path: str) -> List[Dict]:
        """Scan pyproject.toml for LLM packages"""
        try:
            with open(file_path, 'r') as f:
                data = toml.load(f)

            violations = []

            # Check dependencies in various sections
            dependency_sections = [
                'project.dependencies',
                'project.optional-dependencies',
                'tool.poetry.dependencies'
            ]

            for section_path in dependency_sections:
                try:
                    parts = section_path.split('.')
                    current = data
                    for part in parts:
                        current = current[part]

                    if isinstance(current, dict):
                        for package_name, version in current.items():
                            if package_name.lower() in self.llm_packages:
                                violations.append({
                                    'type': 'dependency_violation',
                                    'file': file_path,
                                    'section': section_path,
                                    'package': package_name,
                                    'description': self.llm_packages[package_name.lower()],
                                    'severity': 'critical'
                                })
                    elif isinstance(current, list):
                        for dep in current:
                            # Handle both "package>=version" and "package"
                            package_name = dep.split('>=')[0].split('<=')[0].split('==')[0].strip()
                            if package_name.lower() in self.llm_packages:
                                violations.append({
                                    'type': 'dependency_violation',
                                    'file': file_path,
                                    'section': section_path,
                                    'package': package_name,
                                    'description': self.llm_packages[package_name.lower()],
                                    'severity': 'critical'
                                })

                except KeyError:
                    continue  # Section doesn't exist

            return violations
        except FileNotFoundError:
            return []
        except Exception as e:
            return [{
                'type': 'scan_error',
                'file': file_path,
                'error': str(e),
                'severity': 'medium'
            }]

    def scan_pip_freeze(self) -> List[Dict]:
        """Scan currently installed packages for LLM packages"""
        try:
            result = subprocess.run(['pip', 'freeze'], capture_output=True, text=True, check=True)
            installed_packages = result.stdout.strip().split('\n')

            violations = []
            for pkg_line in installed_packages:
                if '==' in pkg_line:
                    pkg_name = pkg_line.split('==')[0].strip()
                else:
                    pkg_name = pkg_line.strip()

                if pkg_name.lower() in self.llm_packages:
                    violations.append({
                        'type': 'installed_dependency_violation',
                        'package': pkg_name,
                        'description': self.llm_packages[pkg_name.lower()],
                        'severity': 'critical',
                        'message': f"LLM package '{pkg_name}' is installed in environment"
                    })

            return violations
        except subprocess.CalledProcessError:
            return [{
                'type': 'pip_freeze_error',
                'severity': 'medium',
                'message': "Could not run pip freeze to check installed packages"
            }]
        except Exception as e:
            return [{
                'type': 'scan_error',
                'error': str(e),
                'severity': 'medium'
            }]

def run_full_dependency_scan(project_path: str = '.') -> List[Dict]:
    """Run comprehensive dependency scan"""
    scanner = DependencyScanner()
    results = []

    # Check requirements.txt
    req_file = f"{project_path}/requirements.txt"
    results.extend(scanner.scan_requirements_txt(req_file))

    # Check pyproject.toml
    pyproj_file = f"{project_path}/pyproject.toml"
    results.extend(scanner.scan_pyproject_toml(pyproj_file))

    # Check installed packages
    results.extend(scanner.scan_pip_freeze())

    return results
```

## Dynamic Analysis Methods

### 1. Runtime Monitoring

#### Network Traffic Interception
```python
import socket
import threading
import time
from typing import List, Dict
from datetime import datetime

class NetworkMonitor:
    """
    Monitor network traffic for LLM API calls
    """
    def __init__(self):
        self.blocked_domains = [
            'api.openai.com',
            'api.anthropic.com',
            'api.cohere.ai',
            'api.huggingface.co',
            'pinecone.io',
            'weaviate.io',
            'api.llamacloud.com'
        ]
        self.captured_connections = []
        self.monitoring = False

    def start_monitoring(self):
        """Start monitoring network connections"""
        self.monitoring = True
        monitor_thread = threading.Thread(target=self._monitor_loop)
        monitor_thread.daemon = True
        monitor_thread.start()

    def stop_monitoring(self):
        """Stop monitoring network connections"""
        self.monitoring = False

    def _monitor_loop(self):
        """Main monitoring loop"""
        # This is a simplified example - in practice, you'd use a packet capture library
        # like scapy or system tools like tcpdump
        while self.monitoring:
            # Check for connections to blocked domains
            # This is pseudocode - actual implementation would require deeper network inspection
            time.sleep(1)

    def check_blocked_connections(self, domain: str) -> bool:
        """Check if domain is in blocked list"""
        return any(blocked in domain.lower() for blocked in self.blocked_domains)

    def get_violations(self) -> List[Dict]:
        """Get captured violations"""
        return [
            conn for conn in self.captured_connections
            if self.check_blocked_connections(conn['destination'])
        ]

# Alternative: Using environment variables to track API calls
class APICallTracker:
    """
    Track API calls by intercepting HTTP requests
    """
    def __init__(self):
        self.tracked_calls = []
        self.llm_endpoints = [
            'openai.com',
            'anthropic.com',
            'cohere.ai',
            'huggingface.co',
            'pinecone.io',
            'weaviate.io'
        ]

    def track_request(self, method: str, url: str, headers: dict = None, body: str = None):
        """Track an HTTP request"""
        for endpoint in self.llm_endpoints:
            if endpoint in url.lower():
                self.tracked_calls.append({
                    'timestamp': datetime.utcnow().isoformat(),
                    'method': method,
                    'url': url,
                    'headers': headers,
                    'body_preview': body[:200] if body else None,
                    'severity': 'critical',
                    'violation_type': 'llm_api_call'
                })
                return True  # This is a violation
        return False  # Not a violation

# Example of monkey-patching requests library to track calls
import requests
original_request = requests.Session.request

def tracked_request(self, method, url, **kwargs):
    tracker = getattr(self, '_api_tracker', APICallTracker())
    is_violation = tracker.track_request(method, url, kwargs.get('headers'), str(kwargs.get('data', '')))

    if is_violation:
        print(f"🚨 LLM API CALL DETECTED: {method} {url}")

    # Store tracker on session for persistence
    self._api_tracker = tracker

    # Call original request
    return original_request(self, method, url, **kwargs)

# Apply the patch
requests.Session.request = tracked_request
```

### 2. Container/Process Monitoring

#### Docker Container Analysis
```python
import subprocess
import json
from typing import List, Dict

class ContainerAnalyzer:
    """
    Analyze running containers for LLM dependencies
    """

    def check_container_dependencies(self, container_id: str) -> List[Dict]:
        """Check dependencies in a running container"""
        violations = []

        try:
            # List installed Python packages in container
            result = subprocess.run([
                'docker', 'exec', container_id,
                'pip', 'list', '--format', 'json'
            ], capture_output=True, text=True, check=True)

            packages = json.loads(result.stdout)

            llm_packages = [
                'openai', 'anthropic', 'cohere', 'transformers', 'langchain',
                'llama-index', 'pinecone-client', 'weaviate', 'chromadb'
            ]

            for pkg in packages:
                if pkg['name'].lower() in llm_packages:
                    violations.append({
                        'type': 'container_dependency_violation',
                        'container_id': container_id,
                        'package': pkg['name'],
                        'version': pkg['version'],
                        'severity': 'critical'
                    })

        except subprocess.CalledProcessError:
            violations.append({
                'type': 'container_analysis_error',
                'container_id': container_id,
                'severity': 'medium',
                'message': "Could not analyze container dependencies"
            })
        except Exception as e:
            violations.append({
                'type': 'analysis_error',
                'container_id': container_id,
                'error': str(e),
                'severity': 'medium'
            })

        return violations

    def check_image_layers(self, image_name: str) -> List[Dict]:
        """Check Docker image layers for LLM-related installations"""
        violations = []

        try:
            # Get image history
            result = subprocess.run([
                'docker', 'history', '--format', '{{json .}}', image_name
            ], capture_output=True, text=True, check=True)

            lines = result.stdout.strip().split('\n')
            for line in lines:
                if line:
                    layer_info = json.loads(line)
                    cmd = layer_info.get('CreatedBy', '').lower()

                    # Check for LLM-related installation commands
                    llm_indicators = [
                        'pip install.*openai', 'pip install.*anthropic', 'pip install.*cohere',
                        'pip install.*transformers', 'pip install.*langchain',
                        'apt-get install.*torch', 'yum install.*tensorflow'
                    ]

                    for indicator in llm_indicators:
                        if indicator in cmd:
                            violations.append({
                                'type': 'image_layer_violation',
                                'image': image_name,
                                'command': layer_info['CreatedBy'],
                                'indicator': indicator,
                                'severity': 'critical'
                            })

        except subprocess.CalledProcessError:
            violations.append({
                'type': 'image_analysis_error',
                'image': image_name,
                'severity': 'medium',
                'message': "Could not analyze image layers"
            })
        except Exception as e:
            violations.append({
                'type': 'analysis_error',
                'image': image_name,
                'error': str(e),
                'severity': 'medium'
            })

        return violations
```

## Code Quality and Security Checks

### 1. Complexity Analysis for Agent Patterns

```python
import ast
from typing import List, Dict

class AgentPatternDetector(ast.NodeVisitor):
    """
    Detect potential agent patterns that might indicate AI loops
    """

    def __init__(self):
        self.agent_patterns = []
        self.nested_functions = []
        self.recursion_candidates = []

    def visit_FunctionDef(self, node):
        # Track function nesting
        self.nested_functions.append(node.name)

        # Check for potential recursion
        if self._detect_recursion(node):
            self.recursion_candidates.append({
                'function': node.name,
                'line': node.lineno,
                'severity': 'high',
                'pattern': 'potential_recursion'
            })

        # Check for AI-like decision making
        if self._has_ai_decision_logic(node):
            self.agent_patterns.append({
                'function': node.name,
                'line': node.lineno,
                'severity': 'medium',
                'pattern': 'ai_decision_logic'
            })

        self.generic_visit(node)
        self.nested_functions.pop()

    def visit_While(self, node):
        # Check for while loops that might be agent loops
        if self._is_potential_agent_loop(node):
            self.agent_patterns.append({
                'type': 'while_loop',
                'line': node.lineno,
                'severity': 'high',
                'pattern': 'potential_agent_loop'
            })
        self.generic_visit(node)

    def visit_For(self, node):
        # Check for for loops that might iterate over AI responses
        if self._is_potential_ai_iteration(node):
            self.agent_patterns.append({
                'type': 'for_loop',
                'line': node.lineno,
                'severity': 'medium',
                'pattern': 'potential_ai_iteration'
            })
        self.generic_visit(node)

    def _detect_recursion(self, node) -> bool:
        """Detect if function calls itself (direct or indirect)"""
        # Simplified check - in practice would need more sophisticated analysis
        source = ast.unparse(node)
        return f"{node.name}(" in source and "return" in source

    def _has_ai_decision_logic(self, node) -> bool:
        """Check for patterns that suggest AI-like decision making"""
        source = ast.unparse(node).lower()

        ai_indicators = [
            'think', 'reason', 'analyze', 'evaluate', 'judge',
            'decide', 'choose', 'select', 'consider',
            'if .*score', 'if .*confidence', 'if .*probability'
        ]

        return any(indicator in source for indicator in ai_indicators)

    def _is_potential_agent_loop(self, node) -> bool:
        """Check if while loop might be an agent loop"""
        source = ast.unparse(node).lower()

        agent_indicators = [
            'while true', 'while 1', 'while condition',
            'response', 'generate', 'think', 'act', 'observe'
        ]

        return any(indicator in source for indicator in agent_indicators)

    def _is_potential_ai_iteration(self, node) -> bool:
        """Check if for loop iterates over AI-generated content"""
        source = ast.unparse(node).lower()

        ai_iteration_indicators = [
            'responses', 'generations', 'completions', 'thoughts',
            'for.*response', 'for.*completion', 'for.*generation'
        ]

        return any(indicator in source for indicator in ai_iteration_indicators)
```

### 2. Configuration File Analysis

```python
import yaml
import json
import toml
from typing import List, Dict

class ConfigAnalyzer:
    """
    Analyze configuration files for LLM-related settings
    """

    def __init__(self):
        self.llm_indicators = [
            'openai', 'anthropic', 'cohere', 'huggingface',
            'api_key', 'llm', 'ai', 'model', 'embedding',
            'vector', 'semantic', 'transformers'
        ]

    def analyze_yaml_config(self, file_path: str) -> List[Dict]:
        """Analyze YAML configuration file"""
        try:
            with open(file_path, 'r') as f:
                config = yaml.safe_load(f)

            violations = []
            self._scan_config_recursive(config, file_path, violations, [])

            return violations
        except Exception as e:
            return [{
                'type': 'config_analysis_error',
                'file': file_path,
                'error': str(e),
                'severity': 'medium'
            }]

    def analyze_json_config(self, file_path: str) -> List[Dict]:
        """Analyze JSON configuration file"""
        try:
            with open(file_path, 'r') as f:
                config = json.load(f)

            violations = []
            self._scan_config_recursive(config, file_path, violations, [])

            return violations
        except Exception as e:
            return [{
                'type': 'config_analysis_error',
                'file': file_path,
                'error': str(e),
                'severity': 'medium'
            }]

    def analyze_env_file(self, file_path: str) -> List[Dict]:
        """Analyze environment variable file"""
        try:
            with open(file_path, 'r') as f:
                lines = f.readlines()

            violations = []
            for i, line in enumerate(lines, 1):
                line = line.strip()
                if line and not line.startswith('#'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key_lower = key.lower()

                        # Check for LLM-related environment variables
                        if any(indicator in key_lower for indicator in ['openai', 'anthropic', 'cohere', 'llm', 'ai']):
                            violations.append({
                                'type': 'env_var_violation',
                                'file': file_path,
                                'line': i,
                                'variable': key,
                                'severity': 'high',
                                'message': f"Potential LLM API key or configuration: {key}"
                            })

                        # Check for API key patterns in values
                        value_lower = value.lower()
                        if any(provider in value_lower for provider in ['sk-', 'ak-', 'org-']):  # Common API key prefixes
                            if any(indicator in key_lower for indicator in ['key', 'token', 'secret']):
                                violations.append({
                                    'type': 'api_key_violation',
                                    'file': file_path,
                                    'line': i,
                                    'variable': key,
                                    'severity': 'critical',
                                    'message': f"Potential API key detected in environment variable: {key}"
                                })

            return violations
        except Exception as e:
            return [{
                'type': 'config_analysis_error',
                'file': file_path,
                'error': str(e),
                'severity': 'medium'
            }]

    def _scan_config_recursive(self, obj, file_path: str, violations: List[Dict], path: List[str]):
        """Recursively scan configuration for LLM indicators"""
        if isinstance(obj, dict):
            for key, value in obj.items():
                current_path = path + [key]

                key_lower = key.lower()
                if any(indicator in key_lower for indicator in self.llm_indicators):
                    violations.append({
                        'type': 'config_violation',
                        'file': file_path,
                        'path': '.'.join(current_path),
                        'key': key,
                        'severity': 'medium',
                        'message': f"Potential LLM configuration detected: {'.'.join(current_path)}"
                    })

                # Recurse into nested objects
                self._scan_config_recursive(value, file_path, violations, current_path)

        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                current_path = path + [str(i)]
                self._scan_config_recursive(item, file_path, violations, current_path)
```

These auditing techniques provide comprehensive coverage for detecting LLM integration violations in codebases, from static analysis to dynamic monitoring.