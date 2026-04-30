# Hybrid Intelligence Architect Skill

This skill provides expertise in selective LLM integration using Claude Agent SDK. Specialized in implementing premium-gated features like adaptive learning paths and LLM-graded assessments while maintaining strict isolation from deterministic logic.

## Components

### SKILL.md
Core instructions and patterns for hybrid intelligence system design with focus on:
- Selective LLM integration strategies
- Claude Agent SDK implementation patterns
- Premium-gated feature architecture
- Deterministic logic isolation
- Error handling and fallback mechanisms

### References
- `llm-integration-patterns.md` - Comprehensive guide for LLM integration with Claude Agent SDK
- `premium-features.md` - Implementation guide for premium-gated features with access control
- `deterministic-logic-isolation.md` - Patterns for maintaining strict separation between deterministic and AI-enhanced logic

### Scripts
- `generate-feature-guard.py` - Generates feature guard decorators and access control classes for premium features
- `generate-claude-integration.py` - Generates Claude Agent SDK integration patterns with fallback mechanisms

### Assets
- `implementation-patterns.md` - Common implementation patterns for hybrid intelligence systems

## Usage

Use this skill when designing and implementing hybrid intelligence systems that:
- Integrate LLMs selectively for enhanced functionality
- Implement premium-gated features using Claude Agent SDK
- Create adaptive learning paths based on user performance
- Develop LLM-graded assessments with quality controls
- Maintain strict separation between deterministic and AI-enhanced logic
- Ensure data privacy and security in AI-enabled systems

## Quick Start

### For Feature Guard Generation:
```bash
python scripts/generate-feature-guard.py --feature-name "adaptive-learning" --service-name "AdaptiveLearningService" --tier PREMIUM --output-dir ./generated
```

### For Claude Integration:
```bash
python scripts/generate-claude-integration.py --output-dir ./generated
```