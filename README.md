# 🚀 Naveed's AI Skills Library

**104+ production-ready AI skills** to supercharge Claude Code, GitHub Copilot, Cursor, and any LLM.

⚡ Build faster · ⚡ Automate workflows · ⚡ Deploy production systems · ⚡ Create powerful AI agents

Built from real hackathons and production-grade systems.

<div align="center">

[![Skills](https://img.shields.io/badge/Skills-104+-f59e0b?style=for-the-badge)](https://github.com/NaveedTechLab/skills-library)
[![Claude Code](https://img.shields.io/badge/Claude_Code-Compatible-412991?style=for-the-badge&logo=anthropic&logoColor=white)](https://github.com/NaveedTechLab/skills-library)
[![Cursor](https://img.shields.io/badge/Cursor-Compatible-000000?style=for-the-badge)](https://github.com/NaveedTechLab/skills-library)
[![Copilot](https://img.shields.io/badge/GitHub_Copilot-Compatible-2088FF?style=for-the-badge&logo=github&logoColor=white)](https://github.com/NaveedTechLab/skills-library)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

</div>

---

## 💡 What You Can Do With This

- Build full-stack apps in minutes (FastAPI, Next.js)
- Deploy apps to Kubernetes with best practices
- Create AI agents without starting from scratch
- Automate business workflows (CRM, WhatsApp, Email)
- Generate content, quizzes, and documentation instantly

---

## ⚡ 30-Second Demo

```bash
/fastapi-backend-builder
# 👉 Creates production-ready FastAPI app (auth + DB)

/quiz-generator
# 👉 Generates 50 MCQs instantly

/kubernetes-deployer
# 👉 Deploys your app to Kubernetes

/mcp-builder
# 👉 Builds MCP servers for APIs (Stripe, Gmail, etc.)
```

---

## ⭐ Most Popular Skills

| Skill | What it Does |
|-------|-------------|
| `fastapi-backend-builder` | Production FastAPI app with auth + DB |
| `kubernetes-deployer` | Deploy any app to Kubernetes |
| `mcp-builder` | Build MCP servers for any API |
| `quiz-generator` | Generate 50 MCQs from any content |
| `whatsapp-watcher` | WhatsApp automation agent |
| `summary-generator` | Auto-summarize any document |

---

## 🧠 What is a Skill?

A **Skill** is a Markdown file (`SKILL.md`) that gives AI tools deep, specialized knowledge and step-by-step execution instructions.

Think of it as: **"Reusable AI Brain"**

Each skill includes:
- What to do
- How to do it
- Best practices
- Common mistakes
- Real examples

---

## ⚙️ Quick Start (Claude Code)

```bash
# Clone repo
git clone https://github.com/NaveedTechLab/skills-library.git

# Go to your project
cd your-project

# Add skills
mkdir -p .claude/skills
cp -r ../skills-library/skills/fastapi-backend-builder .claude/skills/
```

Start using:

```
/fastapi-backend-builder  Build a scalable backend with JWT auth
```

---

## 🧩 Works With

| Tool | How to Use |
|------|-----------|
| **Claude Code** | Copy to `.claude/skills/` → `/skill-name` |
| **GitHub Copilot** | Paste into `.github/copilot-instructions.md` |
| **Cursor** | Add to `.cursorrules` or `@file` reference |
| **Windsurf** | Add to `.windsurfrules` |
| **Continue.dev** | Reference via `@file` in chat |
| **ChatGPT / Gemini** | Paste `SKILL.md` content as context |

---

## 🌍 Available on SkillHub

These skills are indexed and discoverable via:

```bash
npx skillhub search "naveed" --limit 10
```

Install directly:

```bash
npx skillhub install NaveedTechLab/skills-library/fastapi-backend-builder --project
```

---

## 📦 Skill Categories

### ☁️ Cloud & DevOps
`k8s-foundation` · `kubernetes-deployer` · `argocd-app-deployment` · `kafka-k8s-setup` · `postgres-k8s-setup` · `prometheus-grafana-setup` · `nextjs-k8s-deploy` · `infra-deployment-specialist` · `infra_devops`

### ⚙️ Backend Development
`fastapi-backend-builder` · `fastapi-dapr-agent` · `fastapi-engineer` · `backend-rest-api` · `backend-ai-microservice` · `realtime-websocket-system` · `database-postgresql-design` · `event-driven-architect` · `event_streaming`

### 🎨 Frontend Development
`nextjs-ui-builder` · `frontend-design` · `frontend-developer` · `frontend-react-dashboard` · `frontend-ai-form-builder` · `motion-interaction-designer` · `threejs-react-ui-specialist` · `webgl-performance-optimizer` · `ui-ux-futuristic-designer` · `canvas-design` · `algorithmic-art`

### 🤖 AI Agents & MCP
`mcp-builder` · `mcp-code-execution` · `browser-payment-mcp` · `orchestrator-engine` · `a2a-messaging` · `agents-md-gen` · `hybrid-intelligence-architect`

### 📲 Automation & Watchers
`gmail-watcher` · `whatsapp-watcher` · `filesystem-watcher` · `finance-watcher` · `base-watcher-framework` · `watchdog-process-manager` · `linkedin-posting-automation` · `scheduler-cron-integration` · `audit-logging-system`

### 📱 Social & Communication
`slack-mcp-server` · `slack-gif-creator` · `twitter-mcp-server` · `meta-social-mcp-server` · `email-mcp-server` · `calendar-mcp-server` · `internal-comms`

### 📚 Education & Learning
`quiz-master` · `quiz-generator` · `socratic-tutor` · `concept-explainer` · `concept-scaffolding` · `assessment-builder` · `exercise-designer` · `learning-objectives` · `progress-motivator` · `ai-collaborate-teaching`

### 📄 Documents & Office
`docx` · `pdf` · `pptx` · `xlsx` · `doc-coauthoring` · `notebooklm-slides`

### 🏢 CRM & Business
`crm_database_management` · `channel_ingestion` · `agent_workflow` · `odoo-mcp-server` · `business-audit-generator`

### 🧪 QA & Testing
`webapp-testing` · `qa-testing-specialist` · `qa-auditor` · `qa-debugging-performance` · `qa_automation` · `code-validation-sandbox` · `security-sandbox-controls`

### ✍️ Content & Writing
`book-scaffolding` · `summary-generator` · `technical-clarity` · `prompt-template-designer` · `canonical-format-checker` · `session-intelligence-harvester` · `skills-proficiency-mapper` · `ux-evaluator` · `tool-selection-framework`

---

## 🤝 Contributing

```
skills/
  skill-name/
    SKILL.md          # Required
    templates/        # Optional
    scripts/          # Optional
    references/       # Optional
```

Each `SKILL.md` must include:
- Overview & use cases
- Step-by-step instructions
- Real examples
- Common mistakes
- When NOT to use this

---

## 👨‍💻 About the Creator

Built by **[NaveedTechLab](https://github.com/NaveedTechLab)**
Full Stack AI Engineer — Agent Systems & Automation

Focused on:
- AI Agents & MCP Servers
- Automation Systems
- Scalable Backend Architectures

---

## ⭐ Support

If this helps you:

- ⭐ **Star the repo**
- 🍴 **Fork and build on it**
- 📢 **Share with developers**

Let's build smarter with AI 🚀
