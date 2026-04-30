#!/usr/bin/env python3
"""
Zero-Backend-LLM Violation Remediator
Automatically fixes common LLM integration violations in codebases
"""

import os
import re
import sys
import ast
import argparse
from pathlib import Path
from typing import List, Dict, Tuple
from datetime import datetime

class ViolationRemediator:
    """
    Automatically remediates LLM integration violations
    """

    def __init__(self):
        self.remediation_patterns = [
            # Remove OpenAI imports
            {
                'pattern': r'^(\s*)import openai\s*$',
                'replacement': r'# REMOVED: \1import openai  # Zero-Backend-LLM compliance',
                'description': 'OpenAI import removal'
            },
            {
                'pattern': r'^(\s*)from openai import.*$',
                'replacement': r'# REMOVED: \1from openai import  # Zero-Backend-LLM compliance',
                'description': 'OpenAI import removal'
            },

            # Remove Anthropic imports
            {
                'pattern': r'^(\s*)import anthropic\s*$',
                'replacement': r'# REMOVED: \1import anthropic  # Zero-Backend-LLM compliance',
                'description': 'Anthropic import removal'
            },
            {
                'pattern': r'^(\s*)from anthropic import.*$',
                'replacement': r'# REMOVED: \1from anthropic import  # Zero-Backend-LLM compliance',
                'description': 'Anthropic import removal'
            },

            # Replace OpenAI API calls with stubs
            {
                'pattern': r'openai\.ChatCompletion\.create\((.*?)\)',
                'replacement': r'stub_openai_chat_completion_create(\1)',
                'description': 'OpenAI ChatCompletion replacement'
            },
            {
                'pattern': r'openai\.Completion\.create\((.*?)\)',
                'replacement': r'stub_openai_completion_create(\1)',
                'description': 'OpenAI Completion replacement'
            },
            {
                'pattern': r'client\.chat\.completions\.create\((.*?)\)',
                'replacement': r'stub_client_chat_completions_create(\1)',
                'description': 'OpenAI client replacement'
            },

            # Replace Anthropic API calls
            {
                'pattern': r'client\.messages\.create\((.*?)\)',
                'replacement': r'stub_client_messages_create(\1)',
                'description': 'Anthropic client replacement'
            },

            # Remove LangChain imports
            {
                'pattern': r'^(\s*)import langchain\s*$',
                'replacement': r'# REMOVED: \1import langchain  # Zero-Backend-LLM compliance',
                'description': 'LangChain import removal'
            },
            {
                'pattern': r'^(\s*)from langchain import.*$',
                'replacement': r'# REMOVED: \1from langchain import  # Zero-Backend-LLM compliance',
                'description': 'LangChain import removal'
            },

            # Remove vector database imports
            {
                'pattern': r'^(\s*)import (pinecone|weaviate|chromadb)\s*$',
                'replacement': r'# REMOVED: \1import \2  # Zero-Backend-LLM compliance',
                'description': 'Vector database import removal'
            },
        ]

        self.stub_functions = '''
# Zero-Backend-LLM Compliance Stubs
# These functions replace LLM API calls with deterministic alternatives

def stub_openai_chat_completion_create(**kwargs):
    """
    Stub function replacing openai.ChatCompletion.create()
    Returns deterministic response for compliance.
    """
    # Log the attempt for audit purposes
    print("WARNING: Attempted to call OpenAI API - returning stub response")

    # Return a deterministic response based on the input
    messages = kwargs.get('messages', [])
    if messages:
        user_message = next((msg for msg in messages if msg.get('role') == 'user'), {})
        user_content = user_message.get('content', '')

        if 'hello' in user_content.lower():
            return {"choices": [{"message": {"content": "Hello! This is a stub response for compliance."}}]}
        elif 'help' in user_content.lower():
            return {"choices": [{"message": {"content": "I can help with basic queries. This is a stub response for compliance."}}]}
        else:
            return {"choices": [{"message": {"content": "This is a stub response for Zero-Backend-LLM compliance."}}]}
    else:
        return {"choices": [{"message": {"content": "Default stub response for compliance."}}]}

def stub_openai_completion_create(**kwargs):
    """
    Stub function replacing openai.Completion.create()
    Returns deterministic response for compliance.
    """
    print("WARNING: Attempted to call OpenAI API - returning stub response")
    prompt = kwargs.get('prompt', 'Default prompt')

    return {"choices": [{"text": f"Stub response for prompt: {prompt[:50]}... [COMPLIANCE STUB]"}]}

def stub_client_chat_completions_create(**kwargs):
    """
    Stub function replacing client.chat.completions.create()
    Returns deterministic response for compliance.
    """
    print("WARNING: Attempted to call OpenAI API - returning stub response")
    messages = kwargs.get('messages', [])

    if messages:
        user_message = next((msg for msg in messages if msg.get('role') == 'user'), {})
        user_content = user_message.get('content', '')
        return {"choices": [{"message": {"content": f"Stub response for: {user_content[:50]}... [COMPLIANCE STUB]"}}]}
    else:
        return {"choices": [{"message": {"content": "Default stub response [COMPLIANCE STUB]"}}]}

def stub_client_messages_create(**kwargs):
    """
    Stub function replacing client.messages.create()
    Returns deterministic response for compliance.
    """
    print("WARNING: Attempted to call Anthropic API - returning stub response")
    messages = kwargs.get('messages', [])

    if messages:
        user_message = next((msg for msg in messages if msg.get('role') == 'user'), {})
        user_content = user_message.get('content', '')
        return {"content": [{"text": f"Stub response for: {user_content[:50]}... [COMPLIANCE STUB]"}]}
    else:
        return {"content": [{"text": "Default stub response [COMPLIANCE STUB]"}]}

# Add stub implementations for other common patterns
def stub_embed_text(text):
    """
    Stub function replacing embedding services
    Returns deterministic result for compliance.
    """
    print("WARNING: Attempted to embed text - returning stub result")
    # Return a deterministic "embedding" (actually just a hash of the text)
    return [hash(text) % 1000 / 1000.0 for _ in range(1536)]  # Typical embedding dimension

def stub_generate_response(prompt):
    """
    Stub function replacing generative AI
    Returns deterministic response for compliance.
    """
    print("WARNING: Attempted to generate AI response - returning stub")
    if "hello" in prompt.lower():
        return "Hello! This is a deterministic response for compliance."
    elif "help" in prompt.lower():
        return "I can provide basic information. This is a stub for compliance."
    else:
        return "This is a deterministic response for Zero-Backend-LLM compliance."
'''

    def remove_llm_dependencies(self, requirements_path: str) -> List[str]:
        """
        Remove LLM-related dependencies from requirements.txt
        """
        llm_packages = {
            'openai', 'anthropic', 'cohere', 'transformers', 'huggingface_hub',
            'langchain', 'llama-index', 'crewai', 'autogen',
            'pinecone-client', 'weaviate-client', 'chromadb', 'faiss-cpu',
            'sentence-transformers', 'instructor', 'guidance', 'llm', 'gpt', 'ai'
        }

        with open(requirements_path, 'r') as f:
            lines = f.readlines()

        removed_packages = []
        filtered_lines = []

        for line in lines:
            line_stripped = line.strip()
            if not line_stripped or line_stripped.startswith('#'):
                # Keep comments and empty lines
                filtered_lines.append(line)
                continue

            # Extract package name (handles version specs)
            package_name = re.split(r'[>=<!=~]', line_stripped)[0].strip().lower()

            if package_name in llm_packages:
                removed_packages.append(line_stripped)
                # Add commented version for tracking
                filtered_lines.append(f"# REMOVED: {line}")
            else:
                filtered_lines.append(line)

        # Write the filtered requirements file
        with open(requirements_path, 'w') as f:
            f.writelines(filtered_lines)

        return removed_packages

    def remediate_file(self, file_path: str) -> List[Dict]:
        """
        Remediate a single file by applying patterns
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()

        modified_content = original_content
        changes_made = []

        # Apply each remediation pattern
        for pattern_info in self.remediation_patterns:
            original_length = len(modified_content)

            # Use re.MULTILINE to handle ^ and $ correctly
            modified_content = re.sub(
                pattern_info['pattern'],
                pattern_info['replacement'],
                modified_content,
                flags=re.MULTILINE
            )

            # Check if content changed
            if len(modified_content) != original_length:
                changes_made.append({
                    'file': file_path,
                    'description': pattern_info['description'],
                    'pattern': pattern_info['pattern']
                })

        # Only write if changes were made
        if modified_content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(modified_content)

            # Add stub functions if any API calls were replaced
            if any('replacement' in change['description'].lower() for change in changes_made):
                self._ensure_stub_functions(file_path)

        return changes_made

    def _ensure_stub_functions(self, file_path: str):
        """
        Ensure stub functions are available in the file if API calls were replaced
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Check if stub functions are already present
        if 'stub_openai_chat_completion_create' not in content:
            # Add stub functions at the beginning of the file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(self.stub_functions + '\n\n' + content)

    def remediate_directory(self, directory: str, file_extensions: List[str] = None) -> List[Dict]:
        """
        Remediate all files in directory
        """
        if file_extensions is None:
            file_extensions = ['.py']

        all_changes = []

        for root, dirs, files in os.walk(directory):
            # Skip common directories that shouldn't be modified
            dirs[:] = [d for d in dirs if d not in ['.git', 'node_modules', '__pycache__', '.venv', 'venv', 'dist', 'build']]

            for file in files:
                if any(file.endswith(ext) for ext in file_extensions):
                    file_path = os.path.join(root, file)

                    # Skip if it's the stub functions file itself
                    if 'remediate_violations' in file_path:
                        continue

                    changes = self.remediate_file(file_path)
                    all_changes.extend(changes)

        # Handle requirements.txt if it exists
        requirements_path = os.path.join(directory, 'requirements.txt')
        if os.path.exists(requirements_path):
            removed_packages = self.remove_llm_dependencies(requirements_path)
            if removed_packages:
                all_changes.append({
                    'file': requirements_path,
                    'description': f'Removed {len(removed_packages)} LLM dependencies',
                    'packages_removed': removed_packages
                })

        return all_changes

    def create_backup(self, original_file: str) -> str:
        """
        Create a backup of the original file
        """
        backup_path = f"{original_file}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        import shutil
        shutil.copy2(original_file, backup_path)
        return backup_path

def main():
    parser = argparse.ArgumentParser(description='Zero-Backend-LLM Violation Remediator')
    parser.add_argument('path', help='Path to directory or file to remediate')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would be changed without making changes')
    parser.add_argument('--extensions', nargs='+', default=['.py'],
                        help='File extensions to process (default: .py)')
    parser.add_argument('--backup', action='store_true',
                        help='Create backup files before modifying')

    args = parser.parse_args()

    print("🔧 Starting Zero-Backend-LLM violation remediation...")
    print(f"📁 Target: {args.path}")
    print(f"🧪 Dry run: {'Yes' if args.dry_run else 'No'}")
    print(f"📝 Extensions: {', '.join(args.extensions)}")
    print()

    if not os.path.exists(args.path):
        print(f"❌ Path does not exist: {args.path}")
        sys.exit(1)

    remediator = ViolationRemediator()

    path = Path(args.path)
    changes_made = []

    if path.is_file():
        # Process single file
        if args.backup and not args.dry_run:
            backup_path = remediator.create_backup(str(path))
            print(f"💾 Created backup: {backup_path}")

        if not args.dry_run:
            changes_made = remediator.remediate_file(str(path))
        else:
            print(f"🔍 Would process file: {path}")
            # For dry run, we'll just report what might need fixing
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Simple check for common patterns
            patterns_found = []
            for pattern_info in remediator.remediation_patterns:
                if re.search(pattern_info['pattern'], content, re.MULTILINE):
                    patterns_found.append(pattern_info['description'])

            if patterns_found:
                changes_made = [{'file': str(path), 'description': desc} for desc in set(patterns_found)]
    else:
        # Process directory
        if not args.dry_run:
            changes_made = remediator.remediate_directory(str(path), args.extensions)
        else:
            print(f"🔍 Would scan directory: {path}")
            # For dry run, just report files that would be processed
            files_to_process = []
            for root, dirs, files in os.walk(path):
                dirs[:] = [d for d in dirs if d not in ['.git', 'node_modules', '__pycache__', '.venv', 'venv']]
                for file in files:
                    if any(file.endswith(ext) for ext in args.extensions):
                        files_to_process.append(os.path.join(root, file))

            if files_to_process:
                print(f"   Would process {len(files_to_process)} files")
                changes_made = [{'file': f, 'description': 'Would be scanned'} for f in files_to_process[:10]]  # Show first 10
                if len(files_to_process) > 10:
                    changes_made.append({'file': '...', 'description': f'... and {len(files_to_process) - 10} more'})

    # Report results
    if changes_made:
        print(f"✅ Remediation complete! {len(changes_made)} changes made:")
        print("-" * 60)

        # Group changes by file
        changes_by_file = {}
        for change in changes_made:
            file_path = change['file']
            if file_path not in changes_by_file:
                changes_by_file[file_path] = []
            changes_by_file[file_path].append(change.get('description', 'Unknown change'))

        for file_path, descriptions in changes_by_file.items():
            print(f"📄 {file_path}:")
            for desc in set(descriptions):  # Remove duplicates
                print(f"   • {desc}")
            print()

        # Summary
        total_changes = len(changes_made)
        files_affected = len(changes_by_file)
        print(f"📈 Summary: {total_changes} changes across {files_affected} files")

        if args.dry_run:
            print("ℹ️  This was a dry run - no actual changes were made")
        else:
            print("🎉 Remediation completed successfully!")
    else:
        print("✅ No violations found to remediate!")
        if args.dry_run:
            print("ℹ️  This was a dry run - no actual changes were made")

if __name__ == "__main__":
    main()