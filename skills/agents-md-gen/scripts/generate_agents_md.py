#!/usr/bin/env python3
"""
AGENTS.md Generator Script

This script automatically generates an AGENTS.md file for a repository
according to AAIF standards. It analyzes the repository structure and
creates appropriate documentation for AI agents.
"""

import os
import sys
import json
from pathlib import Path
import argparse


def analyze_repository_structure(repo_path):
    """
    Analyze the repository structure to identify key components
    """
    repo = Path(repo_path)
    
    # Find common directories and files that indicate agent presence
    findings = {
        'directories': [],
        'files': [],
        'agent_configs': [],
        'readme_content': '',
        'main_languages': set(),
        'has_tests': False
    }
    
    # Walk through the repository
    for root, dirs, files in os.walk(repo):
        # Skip common ignore directories
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__', '.git']]
        
        for file in files:
            filepath = Path(root) / file
            
            # Collect directories
            rel_dir = os.path.relpath(root, repo)
            if rel_dir != '.':
                findings['directories'].append(rel_dir)
            
            # Collect files
            findings['files'].append(str(filepath.relative_to(repo)))
            
            # Identify potential agent configuration files
            if file.lower() in ['agent.yaml', 'agent.yml', 'config.yaml', 'config.yml', 
                              'settings.json', 'agents.json', 'skills.json', 'tools.json']:
                findings['agent_configs'].append(str(filepath.relative_to(repo)))
            
            # Identify main programming languages
            if file.endswith(('.py', '.js', '.ts', '.java', '.go', '.rs', '.rb', '.php')):
                ext = file.split('.')[-1]
                findings['main_languages'].add(ext)
            
            # Check for test files
            if 'test' in file.lower() or 'spec' in file.lower():
                findings['has_tests'] = True
    
    # Read README if it exists
    readme_path = repo / 'README.md'
    if readme_path.exists():
        try:
            with open(readme_path, 'r', encoding='utf-8') as f:
                findings['readme_content'] = f.read()[:1000]  # First 1000 chars
        except:
            pass
    
    return findings


def generate_agents_md(findings):
    """
    Generate the AGENTS.md content based on repository analysis
    """
    md_content = """# AGENTS.md - Repository Guide for AI Agents

This document describes the structure, conventions, and guidelines for this repository to help AI agents understand and work with the codebase effectively.

## Repository Overview

This repository contains {language_list} code and follows standard conventions for AI agent development.

""".format(
    language_list=', '.join([f"`.{lang}`" for lang in sorted(findings['main_languages'])]) if findings['main_languages'] else "various programming languages"
)

    # Add directory structure
    if findings['directories']:
        md_content += "## Directory Structure\n\n"
        md_content += "```\n"
        for directory in sorted(set(findings['directories'])):
            md_content += f"{directory}/\n"
        md_content += "```\n\n"

    # Add key files
    if findings['files']:
        md_content += "## Key Files\n\n"
        # Filter for important files
        important_files = []
        for f in findings['files']:
            if any(keyword in f.lower() for keyword in ['readme', 'config', 'main', 'index', 'app']):
                important_files.append(f)
        
        for file in sorted(important_files)[:10]:  # Limit to top 10
            md_content += f"- `{file}`\n"
        if len(important_files) > 10:
            md_content += f"- ... and {len(important_files) - 10} more important files\n"
        md_content += "\n"

    # Add agent configurations
    if findings['agent_configs']:
        md_content += "## Agent Configurations\n\n"
        md_content += "The following files define agent configurations:\n\n"
        for config in findings['agent_configs']:
            md_content += f"- `{config}`\n"
        md_content += "\n"

    # Add conventions section
    md_content += """## Development Conventions

### Code Style
- Follow the established patterns in the existing codebase
- Maintain consistency with existing naming conventions
- Use descriptive variable and function names

### Testing
"""
    if findings['has_tests']:
        md_content += "- Tests are located in test directories throughout the project\n"
        md_content += "- Follow the existing test patterns when adding new functionality\n"
    else:
        md_content += "- Add tests for new functionality following the project's testing patterns\n"

    md_content += """

### Documentation
- Document new functions, classes, and modules appropriately
- Update README.md if adding major new features

## Working with AI Agents

When working with AI agents in this repository:

1. Examine the existing code patterns before making changes
2. Follow the established architecture and design principles
3. Use consistent naming and coding styles
4. Ensure new code integrates well with existing functionality

## Getting Started

1. Review the README.md for initial setup instructions
2. Examine the directory structure and key files mentioned above
3. Look at existing agent configurations to understand the expected format
4. Follow the development conventions outlined in this document

## Additional Notes

Based on the repository analysis, AI agents should pay attention to the following:

- The repository structure suggests it may contain AI agent implementations
- Configuration files (if present) will define agent behavior and capabilities
- Follow the existing code patterns when extending functionality

"""

    return md_content


def main():
    parser = argparse.ArgumentParser(description='Generate AGENTS.md for a repository')
    parser.add_argument('repo_path', nargs='?', default='.', help='Path to the repository (default: current directory)')
    parser.add_argument('-o', '--output', default='AGENTS.md', help='Output file name (default: AGENTS.md)')
    
    args = parser.parse_args()
    
    print(f"Analyzing repository: {os.path.abspath(args.repo_path)}")
    
    # Analyze the repository
    findings = analyze_repository_structure(args.repo_path)
    
    # Generate the AGENTS.md content
    agents_md_content = generate_agents_md(findings)
    
    # Write the output
    with open(args.output, 'w', encoding='utf-8') as f:
        f.write(agents_md_content)
    
    print(f"Generated {args.output} successfully!")
    print(f"Repository has {len(findings['files'])} files and {len(set(findings['directories']))} directories")


if __name__ == "__main__":
    main()