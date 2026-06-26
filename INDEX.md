# 📑 Primitive Index

> Auto-generated index of all available APM primitives

## 📂 Prompts

### 📁 Coding

- **[Copilot Repository Onboarding](/.apm/prompts/coding-copilot-onboarding.prompt.md)** - Onboard a repository to GitHub Copilot by generating a .github/copilot-instructions.md that documents build, test, layout, and validation steps so a coding agent works efficiently from day one.

### 📁 Home Assistant

- **[Home Assistant Automation Renamer](/.apm/prompts/home-assistant-automation-renamer.prompt.md)** - This prompt helps rewrite Home Assistant automation aliases and descriptions into clear, non-technical language that anyone in your household can understand, without changing any automation logic.
- **[Home Assistant Notification Optimizer](/.apm/prompts/home-assistant-notification-optimizer.prompt.md)** - Optimizes Home Assistant automation notifications for Apple Watch and iPhone by rewriting titles and messages to be concise, glanceable, and follow Apple's notification best practices.

## 📐 Instructions

> Long-lived behavior rules deployed to each harness's instruction directory

- **[Devsecninja Conventions](/.apm/instructions/devsecninja-conventions.instructions.md)** (`**`) - DevSecNinja org-wide engineering conventions for AI agents: Conventional-Commit PR titles, pre-PR checks, docs, and no force-push.

## 🧠 Skills

> Model-invoked guides deployed to each harness's skills directory

- **[Commit And Release](/.apm/skills/commit-and-release/SKILL.md)** - Use when asked to commit, write a commit message, stage files, open a pull request, or cut a release in a DevSecNinja repo. Guides Conventional Commit messages, Conventional-Commit PR titles (repos squash-merge), the pre-commit/validate workflow, and the release-please release flow.
- **[Commitment Tracker](/.apm/skills/commitment-tracker/SKILL.md)** - |
- **[Email Follow Up Tracker](/.apm/skills/email-follow-up-tracker/SKILL.md)** - |
- **[Findmeetingtimes Timezone](/.apm/skills/findmeetingtimes-timezone/SKILL.md)** - |
- **[Focus Time Blocker](/.apm/skills/focus-time-blocker/SKILL.md)** - |
- **[Inbox Triage Pass](/.apm/skills/inbox-triage-pass/SKILL.md)** - |
- **[Meeting Transcript Creation](/.apm/skills/meeting-transcript-creation/SKILL.md)** - |
- **[Morning Briefing](/.apm/skills/morning-briefing/SKILL.md)** - |
- **[Obsidian](/.apm/skills/obsidian/SKILL.md)** - Create and edit Obsidian content -- Obsidian Flavored Markdown (wikilinks, embeds, callouts, properties, tags) and Bases (.base database views with filters, formulas, and summaries). Use when working with Obsidian notes or .base files, or when the user mentions wikilinks, callouts, frontmatter, tags, embeds, Bases, table/card views, filters, or formulas in Obsidian.
- **[Ooo Task Handoff Planner](/.apm/skills/ooo-task-handoff-planner/SKILL.md)** - |

## 🧑‍✈️ Agents

> Invocable specialist personas deployed to each harness's agents directory

- **[Ada](/.apm/agents/ada.agent.md)** - Use when working in a personal knowledge vault / Second Brain: ingest, distill, link, lint, and answer from notes. Ada is a librarian and thinking partner who surfaces connections, gaps, and contradictions, cites vault pages, never invents, and confirms before destructive or schema changes.
- **[Dutch Housing Advisor](/.apm/agents/dutch-housing-advisor.agent.md)** - Use when: helping users find, compare, and evaluate homes in the Netherlands, including Dutch housing market research, Funda searches, buying or renting process guidance, bidding strategy, legal considerations, mortgages, VvE, erfpacht, NHG, transfer tax, and neighborhood due diligence.
- **[Personal Assistant](/.apm/agents/personal-assistant.agent.md)** - Personal executive assistant persona that manages email, calendar, and Teams through Work IQ MCP tools - triages and summarizes the inbox, finds meeting times and manages the schedule, summarizes and drafts Teams messages, and tracks commitments and follow-ups, always drafting in the user's voice and confirming before any irreversible action. Use as the orchestrating persona for day-to-day Microsoft 365 productivity.

## 🤝 Bundled Agents

> External agents pulled via APM dependencies, committed here as a reviewable snapshot (see `apm.yml`)

- **[Accessibility Expert](/.github/agents/accessibility.agent.md)** - Expert assistant for web accessibility (WCAG 2.1/2.2), inclusive UX, and a11y testing
- **[ADR Generator](/.github/agents/adr-generator.agent.md)** - Expert agent for creating comprehensive Architectural Decision Records (ADRs) with structured formatting optimized for AI consumption and human readability.
- **[DevOps Expert](/.github/agents/devops-expert.agent.md)** - DevOps specialist following the infinity loop principle (Plan → Code → Build → Test → Release → Deploy → Operate → Monitor) with focus on automation, collaboration, and continuous improvement
- **[GitHub Actions Expert](/.github/agents/github-actions-expert.agent.md)** - GitHub Actions specialist focused on secure CI/CD workflows, action pinning, OIDC authentication, permissions least privilege, and supply-chain security
- **[LinkedIn Post Writer](/.github/agents/linkedin-post-writer.agent.md)** - Draft and format compelling LinkedIn posts with Unicode bold/italic styling, visual separators, and engagement-optimized structure. Transforms raw content, technical material, images, or ideas into copy-paste-ready LinkedIn posts.
- **[Project Architecture Planner](/.github/agents/project-architecture-planner.agent.md)** - Holistic software architecture planner that evaluates tech stacks, designs scalability roadmaps, performs cloud-agnostic cost analysis, reviews existing codebases, and delivers interactive Mermaid diagrams with HTML preview and draw.io export
- **[Prompt Builder](/.github/agents/prompt-builder.agent.md)** - Expert prompt engineering and validation system for creating high-quality prompts - Brought to you by microsoft/edge-ai
- **[sast-sca-security-analyzer](/.github/agents/sast-sca-security-analyzer.agent.md)** - Use when: performing SAST (Static Application Security Testing), SCA (Software Composition Analysis), scanning source code or binaries for security flaws, auditing third-party dependency vulnerabilities, checking policy compliance, generating structured security reports, identifying CWE-mapped flaws with file/line precision, reviewing open-source license risk, or producing CI/CD-gate security findings.
- **[SE: Security](/.github/agents/se-security-reviewer.agent.md)** - Security-focused code review specialist with OWASP Top 10, Zero Trust, LLM security, and enterprise security standards
- **[SE: Tech Writer](/.github/agents/se-technical-writer.agent.md)** - Technical writing specialist for creating developer documentation, technical blogs, tutorials, and educational content
- **[SE: UX Designer](/.github/agents/se-ux-ui-designer.agent.md)** - Jobs-to-be-Done analysis, user journey mapping, and UX research artifacts for Figma and design workflows
- **[Software Engineer Agent](/.github/agents/software-engineer-agent-v1.agent.md)** - Expert-level software engineering agent. Deliver production-ready, maintainable code. Execute systematically and specification-driven. Document comprehensively. Operate autonomously and adaptively.
- **[Task Planner Instructions](/.github/agents/task-planner.agent.md)** - Task planner for creating actionable implementation plans - Brought to you by microsoft/edge-ai

## 🤖 GitHub Copilot Prompts

> Prompts optimized for use with GitHub Copilot in this repository

- **[Copilot Add Prompt](/.github/prompts/copilot-add-prompt.prompt.md)** - Add a new prompt primitive to the AI Toolkit by authoring it under .apm/prompts/ with the right frontmatter
- **[Copilot Generate Informal Message](/.github/prompts/copilot-generate-informal-message.prompt.md)** - Creates an informal message to share a prompt from the repository with your team

---

*This index is automatically generated from the `.apm/` primitives.*
