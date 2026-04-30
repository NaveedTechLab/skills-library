# Naveed's Claude Code Skills Library

> 104 reusable AI skills built across hackathons and real projects — covering cloud-native infra, full-stack dev, AI agents, automation, education, CRM, and more.

---

## What is a Skill?

A **Skill** is a Markdown file (`SKILL.md`) that gives any AI tool deep, specialized knowledge and step-by-step instructions for a specific task. Think of it as a "cheat sheet on steroids" — instead of explaining the same thing every time, you drop a skill into your project and the AI already knows exactly what to do.

Each skill contains:
- **What it does** — clear purpose and scope
- **How to do it** — detailed process, commands, best practices
- **What to avoid** — common mistakes and anti-patterns
- **References** — schemas, examples, external docs

---

## How to Use in Claude Code (Primary Tool)

Claude Code reads skills from `.claude/skills/` inside your project.

### Step 1 — Copy skills into your project

```bash
# Copy a single skill
cp -r skills/mcp-builder /your-project/.claude/skills/

# Copy multiple skills
cp -r skills/fastapi-backend-builder skills/kubernetes-deployer /your-project/.claude/skills/

# Copy ALL skills
cp -r skills/* /your-project/.claude/skills/
```

### Step 2 — Use the skill in conversation

Just mention it naturally, or use `/` to invoke it:

```
/mcp-builder    # invoke directly
/fastapi-backend-builder
/kubernetes-deployer
```

Or just describe your task and Claude Code will automatically use the relevant skill:

```
"Build me an MCP server for Gmail integration"
"Deploy this FastAPI app to Kubernetes"
"Create a quiz for this Python chapter"
```

### Step 3 — Configure in CLAUDE.md (optional)

Add to your project's `CLAUDE.md` to always load specific skills:

```markdown
## Active Skills
- mcp-builder: Use when building MCP servers
- fastapi-backend-builder: Use for all FastAPI work
- kubernetes-deployer: Use for K8s deployments
```

---

## How to Use in Cursor

Cursor reads context from `.cursorrules` or `@` references.

### Method 1 — Add to `.cursorrules`

```bash
# Copy skill content into your .cursorrules
cat skills/fastapi-backend-builder/SKILL.md >> .cursorrules
```

### Method 2 — Reference with @

1. Copy the skill file into your project
2. In Cursor chat, type `@fastapi-backend-builder` to include it as context
3. Ask your question

### Method 3 — Cursor Rules (global)

Place skills in `~/.cursor/rules/` for global availability:

```bash
cp skills/mcp-builder/SKILL.md ~/.cursor/rules/mcp-builder.md
```

---

## How to Use in GitHub Copilot (VS Code)

### Method 1 — Copilot Custom Instructions

1. Open VS Code Settings → search "Copilot Instructions"
2. Paste the content of a `SKILL.md` into the custom instructions box
3. Copilot will follow those instructions in all suggestions

### Method 2 — Workspace Context File

Create `.github/copilot-instructions.md` in your repo:

```bash
cat skills/fastapi-backend-builder/SKILL.md > .github/copilot-instructions.md
```

Copilot automatically reads this file for workspace context.

### Method 3 — Chat Reference

In Copilot Chat, use `#file` to attach a skill:

```
#file:skills/kubernetes-deployer/SKILL.md   deploy this app to k8s
```

---

## How to Use in Windsurf (Codeium)

### Method 1 — `.windsurfrules`

```bash
cat skills/nextjs-ui-builder/SKILL.md > .windsurfrules
```

### Method 2 — Global Rules

Place in `~/.codeium/windsurf/memories/` for project-wide context.

---

## How to Use in Continue.dev

### Add to `config.json`

```json
{
  "contextProviders": [
    {
      "name": "file",
      "params": {
        "nRetrieve": 10
      }
    }
  ],
  "systemMessage": "<paste SKILL.md content here>"
}
```

Or use `@file` in chat to reference a skill:

```
@file skills/mcp-builder/SKILL.md   build an MCP server for Slack
```

---

## How to Use in Any AI Chat (ChatGPT, Gemini, Claude.ai, etc.)

For any AI that accepts system prompts or large context:

1. Open `skills/<skill-name>/SKILL.md`
2. Copy the full content
3. Paste it at the start of your conversation as context
4. Then ask your question

**Example:**

```
[Paste contents of mcp-builder/SKILL.md]

---

Now build me an MCP server that connects to the Stripe API with tools for:
- Creating payment intents
- Listing customers
- Processing refunds
```

---

## How to Use with the Anthropic API / Claude SDK

Pass skill content as a system prompt:

```python
import anthropic
from pathlib import Path

client = anthropic.Anthropic()

skill = Path("skills/fastapi-backend-builder/SKILL.md").read_text()

response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=8096,
    system=skill,
    messages=[
        {"role": "user", "content": "Build a FastAPI app with JWT auth and PostgreSQL"}
    ]
)

print(response.content[0].text)
```

---

## Skill Categories

### Cloud-Native & Infrastructure
| Skill | What it Does |
|-------|-------------|
| `k8s-foundation` | Kubernetes cluster setup and core concepts |
| `kubernetes-deployer` | Deploy apps to Kubernetes with best practices |
| `argocd-app-deployment` | GitOps deployments using ArgoCD |
| `kafka-k8s-setup` | Kafka on Kubernetes with Strimzi |
| `postgres-k8s-setup` | PostgreSQL on Kubernetes |
| `prometheus-grafana-setup` | Monitoring stack setup |
| `nextjs-k8s-deploy` | Deploy Next.js to Kubernetes |
| `infra-deployment-specialist` | Full infrastructure deployment |
| `infra_devops` | DevOps practices and pipelines |

### Backend Development
| Skill | What it Does |
|-------|-------------|
| `fastapi-backend-builder` | FastAPI apps with best practices |
| `fastapi-dapr-agent` | FastAPI + Dapr distributed agent |
| `fastapi-engineer` | Advanced FastAPI engineering |
| `backend-rest-api` | REST API design and implementation |
| `backend-ai-microservice` | AI-powered microservices |
| `realtime-websocket-system` | WebSocket real-time systems |
| `database-postgresql-design` | PostgreSQL schema design |
| `event-driven-architect` | Event-driven architecture patterns |
| `event_streaming` | Streaming systems with Kafka/Pulsar |

### Frontend Development
| Skill | What it Does |
|-------|-------------|
| `nextjs-ui-builder` | Next.js UI with Tailwind & shadcn |
| `frontend-design` | Modern UI/UX design patterns |
| `frontend-developer` | Full frontend development |
| `frontend-react-dashboard` | React dashboard components |
| `frontend-ai-form-builder` | AI-powered form generation |
| `motion-interaction-designer` | Framer Motion animations |
| `threejs-react-ui-specialist` | 3D UI with Three.js + React |
| `webgl-performance-optimizer` | WebGL performance tuning |
| `ui-ux-futuristic-designer` | Futuristic UI/UX design |
| `canvas-design` | HTML Canvas graphics |
| `algorithmic-art` | Generative/algorithmic art |

### MCP & AI Tools
| Skill | What it Does |
|-------|-------------|
| `mcp-builder` | Build MCP servers (Python/TypeScript) |
| `mcp-code-execution` | Code execution via MCP |
| `browser-payment-mcp` | Browser automation + payments MCP |
| `agents-md-gen` | Generate AGENTS.md documentation |
| `orchestrator-engine` | Multi-agent orchestration |
| `a2a-messaging` | Agent-to-Agent messaging |
| `hybrid-intelligence-architect` | Hybrid AI system design |

### Automation & Watchers
| Skill | What it Does |
|-------|-------------|
| `gmail-watcher` | Watch & process Gmail automatically |
| `whatsapp-watcher` | WhatsApp automation |
| `filesystem-watcher` | File system change detection |
| `finance-watcher` | Financial data monitoring |
| `base-watcher-framework` | Generic watcher pattern |
| `watchdog-process-manager` | Process monitoring & restart |
| `linkedin-posting-automation` | Auto LinkedIn posts |
| `scheduler-cron-integration` | Cron job scheduling |
| `audit-logging-system` | Audit trail logging |

### Social & Communication
| Skill | What it Does |
|-------|-------------|
| `slack-mcp-server` | Slack MCP integration |
| `slack-gif-creator` | Create & post GIFs to Slack |
| `twitter-mcp-server` | Twitter/X MCP integration |
| `meta-social-mcp-server` | Facebook/Instagram MCP |
| `email-mcp-server` | Email via MCP |
| `calendar-mcp-server` | Calendar MCP server |
| `internal-comms` | Internal team communication tools |

### Education & Learning
| Skill | What it Does |
|-------|-------------|
| `quiz-master` | Generate quizzes from any content |
| `quiz-generator` | Advanced quiz generation |
| `socratic-tutor` | Socratic teaching method |
| `concept-explainer` | Explain complex concepts simply |
| `concept-scaffolding` | Build learning scaffolds |
| `assessment-builder` | Create assessments |
| `exercise-designer` | Design coding exercises |
| `learning-objectives` | Write learning objectives |
| `progress-motivator` | Student motivation system |
| `ai-collaborate-teaching` | AI-human collaborative teaching |

### Documents & Office
| Skill | What it Does |
|-------|-------------|
| `docx` | Create/edit Word documents |
| `pdf` | Generate & process PDFs |
| `pptx` | Create PowerPoint presentations |
| `xlsx` | Excel spreadsheet creation |
| `doc-coauthoring` | Collaborative document writing |
| `notebooklm-slides` | NotebookLM slide generation |

### CRM & Business
| Skill | What it Does |
|-------|-------------|
| `crm_database_management` | CRM database design & management |
| `channel_ingestion` | Multi-channel data ingestion |
| `agent_workflow` | Business workflow automation |
| `odoo-mcp-server` | Odoo ERP MCP integration |
| `business-audit-generator` | Business audit reports |

### Design & Branding
| Skill | What it Does |
|-------|-------------|
| `brand-guidelines` | Brand guideline creation |
| `theme-factory` | Design theme generation |
| `web-artifacts-builder` | Web UI artifacts |
| `visual-asset-workflow` | Visual asset pipeline |
| `image-generator` | AI image generation workflows |

### QA & Testing
| Skill | What it Does |
|-------|-------------|
| `webapp-testing` | Web app test automation |
| `qa-testing-specialist` | QA specialist workflows |
| `qa-auditor` | Code quality auditing |
| `qa-debugging-performance` | Debug & performance testing |
| `qa_automation` | Full QA automation pipeline |
| `code-validation-sandbox` | Code validation in sandbox |
| `security-sandbox-controls` | Security testing controls |

### Content & Writing
| Skill | What it Does |
|-------|-------------|
| `book-scaffolding` | Structure a technical book |
| `summary-generator` | Auto-generate summaries |
| `technical-clarity` | Make technical writing clear |
| `prompt-template-designer` | Design reusable AI prompts |
| `canonical-format-checker` | Check document formats |
| `session-intelligence-harvester` | Extract insights from sessions |
| `skills-proficiency-mapper` | Map skill proficiency levels |
| `ux-evaluator` | UX evaluation framework |
| `tool-selection-framework` | Pick the right tool for a task |

### DevOps & Deployment
| Skill | What it Does |
|-------|-------------|
| `docusaurus-deploy` | Deploy Docusaurus docs site |
| `docusaurus-deployer` | Advanced Docusaurus deployment |
| `implementation-specialist` | Full implementation planning |
| `infra-specialist` | Infrastructure specialist |
| `code-example-generator` | Generate code examples |
| `ralph-wiggum-loop` | Recursive agent loop pattern |

---

## Quick Start — Full Example (Claude Code)

```bash
# 1. Clone this repo
git clone https://github.com/naveed/skills-library.git

# 2. Go to your project
cd my-fastapi-project

# 3. Add the skills you need
mkdir -p .claude/skills
cp -r ../skills-library/skills/fastapi-backend-builder .claude/skills/
cp -r ../skills-library/skills/database-postgresql-design .claude/skills/
cp -r ../skills-library/skills/kubernetes-deployer .claude/skills/

# 4. Open Claude Code and start building
claude
```

Then in Claude Code:
```
/fastapi-backend-builder  Build a user authentication service with JWT and PostgreSQL
```

---

## Contributing

All skills follow this structure:

```
skills/
  <skill-name>/
    SKILL.md          # Main skill file (required)
    references/       # Supporting docs (optional)
    agents/           # Sub-agent definitions (optional)
    templates/        # Code templates (optional)
    scripts/          # Helper scripts (optional)
```

A `SKILL.md` starts with:

```markdown
---
name: skill-name
description: One-line description of what this skill does
---

# Skill Title

## Overview
...
```

---

## License

MIT — free to use, modify, and share.

Built by **Naveed** during Anthropic hackathons.
