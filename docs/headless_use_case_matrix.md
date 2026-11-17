# Splunk Headless Use-Case Matrix

Status: working catalog for demo selection. Verified on November 15, 2026 against public Splunk docs; the source of `splunk/splunk-agent-skills` (commit `488d7c7`, all 32 `SKILL.md` files) and `splunk/splunkctl` (commit `bb5522d`, v0.1.2, including `internal/client` write-safety code); a local splunkctl 0.1.2 binary (`splunkctl schema`); and the live Splunk MCP Server connected to this workspace. See [Section 5](#5-verification-notes) for corrections to the earlier drafts.

## 1. How to read this catalog

Each use case is one customer job, completed without the Splunk Web UI. Every use case carries the same set of filterable fields:

| Field | Question it answers | Values |
|---|---|---|
| Category | What outcome is the team after? | 6 categories ([2.1](#21-category-the-outcome)) |
| Persona | Who owns that outcome? | 9 personas ([2.2](#22-persona-who-owns-the-outcome)) |
| Mode | How is the headless session started? | Interactive, Event, Pipeline, Scheduled ([2.3](#23-mode-and-change-control)) |
| Change | Does it change Splunk, and who approves? | Read, Gated write, Merge-gated ([2.3](#23-mode-and-change-control)) |
| Splunk tech | Which Splunk layers and products does it use? | [2.4](#24-splunk-technology) |
| Third-party tech | Which customer tools does it use, and in what role? | [2.5](#25-third-party-technology-by-role) |
| Maturity | Can we demo it today? | Ready, Caveats, Emerging |

**Maturity.** *Ready*: works with generally available components. *Caveats*: works today but depends on experimental components (splunkctl, Agent Skills) or on documented limits or entitlements. *Emerging*: controlled availability, or the headless path is unverified.

## 2. Taxonomy

### 2.1 Category (the outcome)

Categories describe what the team accomplishes. Delivery mechanisms (CI/CD, IaC, chat) belong to Mode and Third-party tech, not here, because the same job runs from an IDE agent, a pipeline, or an alert.

| Category | Scope | Changes from the draft list |
|---|---|---|
| **Incident Investigation & Triage** | IT and application incidents: what broke, why, blast radius, hand-off | Was "Incident triage". Security incidents moved to Security Operations. |
| **Security Operations** | Detect, triage, investigate, hunt, respond, produce compliance evidence | Was "SecOps & Compliance". Compliance *of the Splunk platform itself* moved to Platform Ops & Governance. |
| **Data Onboarding & Pipelines** | Get data in, shape, route, and tier it, then prove it is usable | Unchanged |
| **Content Authoring & Lifecycle** | Searches, alerts, dashboards, reports, knowledge objects: create, migrate, optimize, clean up | New. This is where most agentic-authoring demos (for example "build a dashboard") belong. "CI/CD" became a mode. |
| **Platform Operations & Governance** | Configure, scale, health-check, upgrade, and secure Splunk, including how agents are allowed in | Was "Cloud & Platform Ops". IaC became a mode or tool. Access and audit governance added. |
| **Extend & Build** | Custom MCP tools, apps, and embedded agents | New. Small, mostly partner and power-user work. |

### 2.2 Persona (who owns the outcome)

Personas are responsibilities, not job titles; one person can hold several (consistent with both source drafts). Agents, CLIs, and pipelines are *heads*, not personas.

| Persona | Owns |
|---|---|
| **Splunk Platform Admin** | The Splunk environment: indexes, apps, access, health, upgrades |
| **Platform / DevOps Engineer** | Customer automation: Git, CI/CD, Terraform, runbooks, and connecting Splunk to them |
| **Data / Pipeline Engineer** | Sources, collection, processing, routing, and data readiness |
| **SRE / IT Ops** | Service reliability and on-call response |
| **Analyst / Power User** | Answers from data: ad hoc searches, reports, dashboards |
| **SOC Analyst** | Triage, investigation, and response for security findings |
| **Detection Engineer / Threat Hunter** | Detection content, coverage, and hunts |
| **Security & Governance Approver** | Who and what, agents included, may read or change Splunk, plus audit evidence |
| **App Developer / Partner** | Splunk apps, visualizations, integrations, embedded agents |

### 2.3 Mode and change control

| Mode | Started by | Typical head |
|---|---|---|
| **Interactive** | A person prompting an agent | IDE or terminal agent (any client in [2.5](#25-third-party-technology-by-role)) |
| **Event** | An alert, webhook, or chat message | Non-interactive agent run (for example `claude -p`, `codex exec`), or an Agent Launchpad agent |
| **Pipeline** | A pull request or merge | CI/CD job |
| **Scheduled** | A timer | cron, CI schedule, or a scheduled Splunk search |

| Change | Meaning | Mechanism |
|---|---|---|
| **Read** | No changes to Splunk | MCP tools; `splunkctl --read-only` for GET commands; `splunkctl --yes search` for SPL (see note) |
| **Gated write** | The agent proposes a change and a person approves this specific run | splunkctl returns `CONFIRMATION_REQUIRED`, then reruns with `--yes`; `splunk-cloud-admin-copilot` makes one approved change |
| **Merge-gated** | Approval is the pull-request review; the pipeline applies | `terraform apply`, ACS, or splunkctl `--yes` in an approved job |

**Note on splunkctl and searches.** splunkctl classifies requests by HTTP method: GET runs unattended, while every POST, PUT, or DELETE goes through the write gate. A search job is a POST, so `splunkctl --read-only search …` is rejected with `READ_ONLY`, and read-only SPL runs as `splunkctl --yes search export …` (the pattern the `splunk-search` skill uses). For searches, the read-only guarantee comes from reviewing the SPL and from a token whose role has no write capabilities, not from the flag. `--read-only` does work for GET commands such as `index list`, `server health`, `license usage`, `introspection queues`, `fired-alert list`, and `whoami`.

### 2.4 Splunk technology

Splunk's headless story has three layers, plus the products being operated.

| Layer | Component | What it gives the agent |
|---|---|---|
| **Knowledge** | Splunk Agent Skills (32, experimental) | Procedures, validation, and guardrails. See the breakdown below. |
| | splunkctl skill (`splunkctl skill install --agent claude\|codex\|both`) | Command selection and write-approval etiquette for splunkctl. It tells the agent to prefer the MCP Server when available and fall back to splunkctl for anything MCP doesn't cover. |
| **Access** | Splunk MCP Server (Splunkbase 7931) | Curated, governed, read-oriented tools: `splunk_` (platform), `saia_` (AI Assistant), `o11y_` (Observability), `es_` (ES 8.7+), `SA-ITOA_` (ITSI 5.0.1+), and admin-defined custom tools |
| | splunkctl (experimental) | Full REST surface, scriptable, JSON output, write approval gate |
| | Product REST APIs | ES API, SOAR API, ITSI API, Data Management API (Edge/Ingest Processor), Observability API |
| | Config as code | ACS CLI; Terraform `splunk/scp` (Cloud), `splunk/splunk` (Enterprise), `signalfx` (Observability) |
| | SDKs | Splunk Python SDK, including the Agentic SDK (`splunklib.ai`) |
| **In-platform intelligence** | Splunk AI Assistant (SAIA) | NL→SPL, explain, optimize, find data (Agent Mode). Reachable headlessly via `saia_` tools. |
| | ES agents | Triage & Response, Detection Builder, Malware Reversing & Phishing, Connector Builder, and others. Results readable headlessly via `es_get_ai_analysis` (Cloud only). |
| | Agent Launchpad | No-code agents launched from searches, alerts, and detections, using approved MCP tools (GA July 2026, Splunk Cloud) |
| | AI Canvas | Multiuser agentic workspace in Cisco Cloud Control; ES data can be used there |

**Agent Skills fall into three kinds**, based on each skill's declared `allowed-tools`. None of the 32 requires MCP.

| Kind | Skills | Touches a stack? |
|---|---|---|
| **Executors** (shell + splunkctl or ACS) | `splunk-search` (read-only SPL), `hec-setup-and-troubleshooting` (`hec send` + verification search), `splunk-identity-saml-readiness-advisor` (read-only searches), `custom-visualization-builder` (build, then `app install`), `splunk-cloud-admin-copilot` (`acs`: read state, one approved CIDR change) | Yes |
| **Builders** (shell or file only) | `splunk-dashboard-converter` (Read only), `splunk-setup-page-builder`, `splunk-enterprise-administration-advisor` | Produce artifacts or local checks |
| **Advisors** (web only) | The other 24, for example `data-source-onboarding-advisor`, `incident-diagnosis-specialist`, `forwarder-and-data-ingest-doctor`, `search-performance-optimizer`, the cluster, upgrade, and governance skills | No; they reason over evidence handed to them |

So most demos have three parts: an **evidence source** (MCP tools or `splunk-search`), an **advisory skill** that interprets the evidence, and, where a change is needed, a **gated splunkctl or ACS write**.

**Products operated:** Splunk Platform (Cloud, Enterprise), Federated Search, Machine Data Lake (MDL), Catalog, Edge Processor, Ingest Processor, Enterprise Security (incl. Detection Studio), SOAR, ITSI, Observability Cloud, plus collection components: Universal Forwarder (UF), Deployment Server, Splunk OTel Collector, and Splunk Operator for Kubernetes.

### 2.5 Third-party technology (by role)

Third-party tools are grouped by the role they play in the workflow, because "Kubernetes", "Terraform", and "Slack" do different jobs.

| Role | Technologies |
|---|---|
| **Agent client** (the head) | Claude Code, OpenAI Codex, Cursor, Gemini CLI, GitHub Copilot, OpenCode |
| **Trigger / orchestrator** | GitHub Actions, GitLab CI, Jenkins, ArgoCD, cron |
| **Change & config tooling** | Terraform / OpenTofu, Ansible, Helm |
| **Environment / data source** | Kubernetes, AWS, Azure, Snowflake, Databricks, Linux hosts |
| **Collaboration & ITSM** (hand-off) | Slack, Microsoft Teams, PagerDuty, ServiceNow, Jira |
| **Model provider** (SDK agents) | OpenAI, Anthropic, Google (Gemini API or Vertex AI), Ollama |
| **Verification** | Playwright (dashboard render checks) |

**The agent client is interchangeable for Interactive use cases.** Agent Skills install into all six clients listed above, and MCP works with any client that supports streamable HTTP (or through `mcp-remote`). So the catalog doesn't tie use cases to a client. Assign clients per demo to show breadth, and treat "same use case, different client" as a demo variant, not a new use case.

## 3. Use-case catalog

Abbreviations: `splunkctl` commands are written without the `splunkctl` prefix. MCP tools keep their namespace prefix.

### 3.1 Incident Investigation & Triage

| ID | Use case | Personas | Mode · Change | Splunk tech | Third-party | Maturity |
|---|---|---|---|---|---|---|
| IR-01 | Ask Splunk from the agent workspace ("which hosts went quiet and what did they log before?") | SRE, Analyst, Admin | Interactive · Read | MCP `splunk_get_metadata`, `splunk_run_query`, `saia_generate_spl`; skill `splunk-search`; `search export` for >1,000 rows | Any client | Ready |
| IR-02 | Fired-alert triage: triggering events, did the page go out, is it throttled | SRE | Interactive · Read | MCP `splunk_list_fired_alerts`, `splunk_get_fired_alert_results`, `splunk_get_alert_action_status`, `splunk_list_active_throttles`; skills `alerting-and-notable-workflows`, `incident-diagnosis-specialist` | PagerDuty, Slack, Jira/ServiceNow | Ready |
| IR-03 | Correlate an app incident across logs, APM traces, and Kubernetes | SRE | Interactive · Read | MCP `o11y_get_apm_service_latency`, `o11y_get_apm_service_dependencies`, `o11y_get_apm_exemplar_traces`, `o11y_search_alerts_or_incidents`, `splunk_run_query`; Observability Cloud | Kubernetes (kubectl), ArgoCD | Caveats |
| IR-04 | ITSI episode triage: blast radius, similar past episodes, linked tickets | SRE | Interactive · Read | MCP `SA-ITOA_get_episodes`, `SA-ITOA_get_impacted_objects`, `SA-ITOA_get_similar_episodes`, `SA-ITOA_get_external_links`; ITSI 5.0.1+ | ServiceNow, Jira | Caveats |
| IR-05 | Alert launches an in-platform agent that gathers evidence and posts a summary | SRE, Admin | Event · Read | Agent Launchpad with approved MCP tools; Splunk Cloud | Slack/Teams | Ready |
| IR-06 | Headless on-call agent: a webhook runs a non-interactive agent that posts a root-cause packet | SRE, Platform/DevOps Eng | Event · Read | `--yes search export` with a read-only role; skills `incident-diagnosis-specialist`, `splunk-search` | PagerDuty, Slack, GitHub Actions; Claude Code or Codex | Caveats |
| IR-07 | Alert-action triage agent built with the Agentic SDK: a custom alert action passes the triggering results to the agent, which returns a structured verdict (severity, service, summary, next steps) and opens a ticket | SRE, App Developer | Event · Read | Agentic SDK (`splunklib.ai`, splunk-sdk 3.0+): `invoke_with_data` for the alert payload, `output_schema`, remote MCP tools allowlisted (`splunk_run_query`), `tool_middleware` audit events written to a Splunk index; packaged as an app with a custom alert action | Jira/ServiceNow, Slack; OpenAI, Anthropic, or Google model | Caveats |
| IR-08 | Multi-agent incident responder: a supervisor delegates log retrieval to a low-cost subagent and root-cause analysis to a specialist subagent, then returns a structured incident summary | SRE, App Developer | Interactive · Read | Agentic SDK: subagents with `input_schema` and `output_schema`, a different model per subagent, local `bin/tools.py` tools tagged by role, `AgentLimits`; remote MCP tools | Ollama (self-hosted model for raw logs); OpenAI, Anthropic, or Google for the specialist | Caveats |

### 3.2 Security Operations

| ID | Use case | Personas | Mode · Change | Splunk tech | Third-party | Maturity |
|---|---|---|---|---|---|---|
| SO-01 | Triage ES findings from the agent workspace: top findings, contributing events, riskiest entities | SOC Analyst | Interactive · Read | MCP `es_` tools (findings, investigations, risk scores, queues), `splunk_run_query`; ES 8.7+ | Any client | Caveats |
| SO-02 | Act on Triage Agent verdicts: read AI analysis, add an investigation note, run a SOAR playbook after approval | SOC Analyst | Event · Gated write | MCP `es_get_ai_analysis`; ES REST API (investigations, notes); SOAR REST API; ES Premier, SOAR; optional hand-off to AI Canvas | ServiceNow/Jira, Slack | Caveats |
| SO-03 | Threat hunt across indexed and federated data | Detection Eng / Hunter | Interactive · Read | MCP `splunk_run_query` (SPL2), `saia_generate_spl`; `search --detach` for long hunts; Federated Search, MDL | AWS (S3, Security Lake), Snowflake, Databricks | Caveats |
| SO-04 | Author a detection with an agent: hypothesis, CIM-aligned SPL, backtest, create in staging | Detection Eng | Interactive · Gated write | Skills `splunk-search`, `field-extraction-and-cim-mapping`, `data-model-and-search-acceleration`; `saved-search add`, `macro add`; ES (Detection Studio / Detection Builder agent as the in-product counterpart) | Any client | Caveats |
| SO-05 | ES detections as code from a CI runner: PR, backtest SPL, deploy on merge, verify enabled and scheduled | Detection Eng, Platform/DevOps Eng | Pipeline · Merge-gated | Validation: `--yes search export` under a read-only token. Deploy, Cloud: content app whose `savedsearches.conf` carries `action.correlationsearch.*` / `action.notable.*`, installed with `acs apps install private` (runs AppInspect). Deploy, Enterprise: `app install --update 1`, or REST `POST /servicesNS/nobody/<app>/saved/searches`. Verify: MCP `splunk_list_alerts`. ES 8; contentctl (customer-managed) | GitLab CI, GitHub Actions | Caveats |
| SO-06 | Compliance evidence pack: privileged access, auth failures, config changes | Governance Approver, SOC Analyst | Scheduled · Read | MCP `splunk_run_saved_search`, `splunk_run_query`; skills `report-authoring-specialist`, `vulnerability-remediation-and-compliance-readiness` | Jira/ServiceNow | Ready |
| SO-07 | Jira alert investigation: correlate related alerts, apply the AI Toolkit model in a saved search, pivot to failure rates, and open a follow-up ticket to block the attacker's IPs after approval ([Lantern](https://lantern.splunk.com/Security_Use_Cases/Automation_and_Orchestration/Leveraging_LLM_reasoning_and_ML_capabilities_for_Jira_alert_investigations)) | SOC Analyst | Interactive · Gated write | MCP `splunk_run_saved_search`, `splunk_run_query` (`apply`); Atlassian MCP (read); `acli jira workitem create` behind a confirmation wrapper; AI Toolkit | Jira | Caveats |

### 3.3 Data Onboarding & Pipelines

| ID | Use case | Personas | Mode · Change | Splunk tech | Third-party | Maturity |
|---|---|---|---|---|---|---|
| DP-01 | Onboard a new sourcetype end to end: intake contract, index, HEC token, test event, parsing and CIM check | Data Eng, Admin | Interactive · Gated write | Skills `data-source-onboarding-advisor`, `ingestion-pipeline-design`, `field-extraction-and-cim-mapping`; `index add`, `hec add`, `hec send`, `field-extraction add`; ACS on Cloud; MCP `splunk_get_sourcetypes` | Any client | Caveats |
| DP-02 | "Logs stopped": find the earliest failing stage, apply an approved fix, re-verify | Data Eng, SRE | Interactive · Gated write | MCP `splunk_get_metadata`, `splunk_run_query` (`_internal`); `introspection queues`, `hec list`, `hec enable`; skills `forwarder-and-data-ingest-doctor`, `hec-setup-and-troubleshooting` | Kubernetes (OTel Collector) | Caveats |
| DP-03 | Kubernetes telemetry via GitOps: OTel Collector Helm values in Git, sync, verify landing | Platform/DevOps Eng, Data Eng | Pipeline · Merge-gated | Splunk OTel Collector Helm chart; `hec add`; MCP `splunk_get_sourcetypes` | Kubernetes, Helm, ArgoCD | Ready |
| DP-04 | SPL2 pipeline as code: filter, mask PII, route | Data Eng | Pipeline · Merge-gated | Data Management API, SPL2; skill `ingestion-pipeline-design`; Edge Processor, Ingest Processor | GitHub Actions | Emerging |
| DP-05 | Data tiering and retention: route to the lake, set retention, search archived data | Data Eng, Admin | Interactive · Gated write | `index edit --param frozenTimePeriodInSecs=…`; skill `index-and-storage-management-advisor`; MDL, Federated Search, Ingest Processor | AWS S3 | Emerging |
| DP-06 | Forwarder fleet change: assign a serverclass, reload, verify clients (Enterprise) | Admin, Data Eng | Interactive · Gated write | `serverclass add`, `serverclass clients`, `forwarder list`, `forwarder reload`; skill `deployment-server-and-forwarder-fleet-management`; UF, Deployment Server | Ansible, Linux hosts | Caveats |
| DP-07 | Data readiness check: find the right data, lag, field coverage, CIM compliance | Data Eng, Analyst | Scheduled · Read | MCP `saia_find_data_source`, `splunk_get_sourcetypes`, `splunk_get_metadata`, `splunk_run_query`; skill `field-extraction-and-cim-mapping`; Catalog | cron | Caveats |
| DP-08 | Migrate Universal Forwarders to an OpenTelemetry-based collector: inventory, plan waves, cut over, prove continuity | Admin, Data Eng | Interactive · Gated write | `forwarder list`, `serverclass clients`; MCP `splunk_get_metadata` before and after; skills `deployment-server-and-forwarder-fleet-management`, `forwarder-and-data-ingest-doctor`; UF, Agent Management, Splunk OTel Collector | Ansible, Linux hosts | Emerging |
| DP-09 | Set up ingest monitoring for a source: no-data, latency, and volume alerts | Data Eng, SRE | Interactive · Gated write | `saved-search add --param …` for alert searches; MCP `splunk_find_silent_alerts`, `splunk_get_alert_details`; skills `alerting-and-notable-workflows`, `forwarder-and-data-ingest-doctor`; Ingest Monitoring app (UI-configured) | Slack, PagerDuty | Caveats |
| DP-10 | Onboard a use case end to end (the uMELT umbrella journey): provision, enroll collectors, connect source, pipeline, monitoring, readiness proof | Platform/DevOps Eng, Data Eng | Pipeline · Merge-gated | Chains DP-03, DP-01, DP-04, DP-09, DP-07: Terraform/ACS for index and HEC, Helm for collectors, Data Management API for the pipeline, splunkctl and MCP for monitoring and verification; skills `data-source-onboarding-advisor`, `ingestion-pipeline-design` | Terraform, Helm, Kubernetes, GitHub Actions | Emerging |

### 3.4 Content Authoring & Lifecycle

| ID | Use case | Personas | Mode · Change | Splunk tech | Third-party | Maturity |
|---|---|---|---|---|---|---|
| CE-01 | Build a dashboard from a prompt: discover data, draft SPL, generate Studio JSON, deploy, check it renders | Analyst, SRE | Interactive · Gated write | MCP discovery tools, `splunk_run_query`; skills `splunk-search`, `report-authoring-specialist`; `dashboard add --file` | Playwright | Caveats |
| CE-02 | Migrate Simple XML dashboards to Dashboard Studio | Admin, Analyst | Pipeline · Merge-gated | Skill `splunk-dashboard-converter`; `dashboard show`, `dashboard add` | GitLab CI, Playwright | Caveats |
| CE-03 | Create or tune an alert from natural language: schedule, trigger, throttle, action, then verify | SRE, Admin | Interactive · Gated write | Skill `alerting-and-notable-workflows`; `saved-search add/edit --param …`; MCP `splunk_get_alert_details` | Slack, PagerDuty | Caveats |
| CE-04 | SPL review gate: a PR that changes searches gets a cost review and an optimized rewrite | Platform/DevOps Eng, Admin | Pipeline · Read | Skills `search-performance-optimizer`, `data-model-and-search-acceleration`; MCP `saia_optimize_spl`; `--yes search export` under a read-only token to compare before and after | GitHub Actions; Claude Code or Codex | Caveats |
| CE-05 | Alert and knowledge-object hygiene: silent, failing, throttled, orphaned | Admin, Governance Approver | Scheduled · Gated write | MCP `splunk_find_silent_alerts`, `splunk_get_alert_action_status`, `splunk_get_knowledge_objects`; skills `knowledge-object-governance`, `dashboard-report-alert-performance-advisor`; `acl set`, `saved-search edit` | cron | Ready |
| CE-06 | Knowledge objects as code with drift detection: searches, macros, lookups, dashboards | Platform/DevOps Eng, Admin | Pipeline · Merge-gated | `saved-search`, `macro`, `lookup`, `lookup-file upload`, `dashboard`; scheduled drift job using `--read-only … list` / `dashboard show` (GET) | GitHub Actions, GitLab CI, Jenkins | Caveats |
| CE-07 | Fix a broken search or dashboard panel: isolate the first failing stage (permissions, macro, lookup, data), hand off the fix | Analyst, Admin | Interactive · Read | Skill `search-and-dashboard-troubleshooter`; `dashboard show`, `macro list`, `lookup list`, `acl show`; MCP `splunk_run_query`, `splunk_get_knowledge_objects`, `saia_explain_spl` | Any client | Caveats |
| CE-08 | Repair a broken saved search in one pass (short-demo variant of CE-07): find the missing macro or unreadable lookup, propose the fix, apply it after approval, rerun the search | Analyst, Admin | Interactive · Gated write | Skill `search-and-dashboard-troubleshooter`; MCP `splunk_get_knowledge_objects`, `splunk_run_query`; `saved-search list`, `macro list`, `lookup list`, `acl show`; fix with `macro add` or `acl set`, which stop at `CONFIRMATION_REQUIRED` | Any client | Caveats |

### 3.5 Platform Operations & Governance

| ID | Use case | Personas | Mode · Change | Splunk tech | Third-party | Maturity |
|---|---|---|---|---|---|---|
| PO-01 | Platform config as code: indexes, HEC tokens, roles, users, allowlists, apps, with drift checks | Platform/DevOps Eng | Pipeline · Merge-gated | Terraform `splunk/scp` (Cloud) or `splunk/splunk` (Enterprise); ACS CLI; `--read-only index list` for drift | Terraform/OpenTofu, GitHub Actions | Caveats |
| PO-02 | Cloud IP allowlist update after an infrastructure change, approved per CIDR | Platform/DevOps Eng, Admin | Event · Gated write | Skill `splunk-cloud-admin-copilot`; ACS CLI | Terraform, AWS | Caveats |
| PO-03 | Health and cluster readiness go/no-go (for example before a rolling restart) | Admin | Interactive · Read | `server health`, `server messages`, `cluster-peers list`, `shcluster-status show`, `maintenance-mode show`; MCP `splunk_get_info`; skills `indexer-cluster-health-and-troubleshooting`, `search-head-cluster-health-and-troubleshooting`, `splunk-health-monitoring-and-diagnostic-collection` | Any client | Ready |
| PO-04 | Upgrade readiness plan: supported path, app and add-on compatibility, go/no-go criteria | Admin | Interactive · Read | Skills `upgrade-and-security-readiness-router`, `upgrade-planning-and-execution-readiness`, `app-and-add-on-lifecycle-advisor`, `splunk-product-question-navigator`; `server info`, `app display` | Ansible | Ready |
| PO-05 | License and capacity forecast | Admin | Scheduled · Read | `license usage`, `license messages`, `index list`; skills `license-and-capacity-planning-advisor`, `index-and-storage-management-advisor` | AWS (SmartStore) | Ready |
| PO-06 | Protect search capacity: find runaway searches, apply a workload rule or disable the search | Admin, SRE | Interactive · Gated write | `jobs list`, `workload-rule add`, `saved-search edit --param disabled=1`; skills `search-performance-optimizer`, `dashboard-report-alert-performance-advisor` | Any client | Caveats |
| PO-07 | Governed agent access: least-privilege role, MCP token, workload pool, audit trail of agent actions | Governance Approver, Admin | Interactive · Gated write | `role add`, `workload-pool add`, `whoami`; MCP token management, `splunk_get_user_info`; `_audit` / `_internal` searches; skill `splunk-identity-saml-readiness-advisor` | Any client | Ready |
| PO-08 | App CI/CD: package, AppInspect, install or upgrade, check whether a restart is needed | Platform/DevOps Eng, App Developer | Pipeline · Merge-gated | Cloud: `acs apps install private` (AppInspect built in), `acs apps install splunkbase`, `acs status current-stack`. Enterprise: `app install --update 1`. Skill `app-and-add-on-lifecycle-advisor` | GitLab CI, GitHub Actions (Lantern ACS starter) | Ready |
| PO-09 | Explain effective access and configuration ("why can't this user see index X?", "which .conf setting wins?") | Admin, Governance Approver | Interactive · Read | Skills `splunk-enterprise-administration-advisor`, `splunk-identity-saml-readiness-advisor`; `--read-only role list`, `user list`, `conf get`; MCP `splunk_get_user_list` | Any client | Ready |
| PO-10 | Splunk CVE exposure: does an advisory apply, patch or exception plan | Admin, Governance Approver | Scheduled · Read | Skills `upgrade-and-vulnerability-readiness-advisor`, `vulnerability-remediation-and-compliance-readiness`; `server info`, `app display`; MCP `splunk_get_info` | Jira/ServiceNow, cron | Ready |
| PO-11 | Generate an agent context document: a Markdown summary of indexes, sourcetypes, apps, saved searches, and versions that agents load at session start instead of rediscovering the environment | Admin, Platform/DevOps Eng, Analyst | Scheduled · Read | `--read-only index list`, `server info`, `app display`, `saved-search list`, `macro list`; MCP `splunk_get_sourcetypes`, `splunk_get_metadata` | Claude Projects, Cursor rules, or `AGENTS.md`; cron | Caveats |
| PO-12 | Scheduled platform digest: collect ingest and health evidence, have advisory skills interpret it, and open a ticket with proposed changes; any write waits for a person | Admin, Platform/DevOps Eng | Scheduled · Read | Evidence: `--read-only server health`, `introspection queues`, `license usage`, `server info`, `app display`; `--yes search export` on `_internal` under a read-only token. Interpretation: skills `forwarder-and-data-ingest-doctor`, `splunk-health-monitoring-and-diagnostic-collection`, `upgrade-planning-and-execution-readiness` | Claude Code or Codex (non-interactive), GitHub Actions or cron, Jira/ServiceNow | Caveats |

### 3.6 Extend & Build

| ID | Use case | Personas | Mode · Change | Splunk tech | Third-party | Maturity |
|---|---|---|---|---|---|---|
| EB-01 | Publish a vetted custom MCP tool (SPL or REST template) for every agent to use | Admin, App Developer | Interactive · Gated write | MCP Server custom tools (`mcp_tool_admin` capability) | Any client | Ready |
| EB-02 | Agent-built Splunk app: setup page, custom visualization, AppInspect, Cloud install, optional embedded agent | App Developer | Interactive · Gated write | Skills `splunk-setup-page-builder`, `custom-visualization-builder`, `app-and-add-on-lifecycle-advisor`; ACS app install; agent harness (controlled availability); Agentic SDK | Any client | Emerging |
| EB-03 | First Splunk agent in about 30 lines of Python: connect, allowlist two MCP tools, ask a question, get structured output | App Developer, Platform/DevOps Eng, Analyst | Interactive · Read | Agentic SDK: `Agent`, `RemoteToolSettings` with `ToolAllowlist` (`splunk_get_indexes`, `splunk_run_query`), `output_schema`, default limits; MCP Server | OpenAI, Anthropic, Google, or Ollama model | Ready |

## 4. Filter indexes

### 4.1 Persona × Category

| Persona | Incident | SecOps | Data | Content | Platform | Build |
|---|---|---|---|---|---|---|
| Splunk Platform Admin | IR-01, IR-05 | | DP-01, DP-05, DP-06, DP-08 | CE-02 – CE-08 | PO-02 – PO-07, PO-09 – PO-12 | EB-01 |
| Platform / DevOps Engineer | IR-06 | SO-05 | DP-03, DP-10 | CE-04, CE-06 | PO-01, PO-02, PO-08, PO-11, PO-12 | EB-03 |
| Data / Pipeline Engineer | | | DP-01 – DP-10 | | | |
| SRE / IT Ops | IR-01 – IR-08 | | DP-02, DP-09 | CE-01, CE-03 | PO-06 | |
| Analyst / Power User | IR-01 | | DP-07 | CE-01, CE-02, CE-07, CE-08 | PO-11 | EB-03 |
| SOC Analyst | | SO-01, SO-02, SO-06 | | | | |
| Detection Engineer / Hunter | | SO-03, SO-04, SO-05 | | | | |
| Security & Governance Approver | | SO-06 | | CE-05 | PO-07, PO-09, PO-10 | |
| App Developer / Partner | IR-07, IR-08 | | | | PO-08 | EB-01 – EB-03 |

### 4.2 Splunk technology → use cases

| Splunk technology | Use cases |
|---|---|
| MCP `splunk_` tools | IR-01, IR-02, IR-03, IR-07, IR-08, SO-01, SO-03, SO-05, SO-06, DP-01, DP-02, DP-03, DP-07 – DP-10, CE-01, CE-03, CE-05, CE-07, CE-08, PO-03, PO-07, PO-09, PO-10, PO-11, EB-03 |
| MCP `saia_` tools / AI Assistant | IR-01, SO-03, DP-07, CE-04, CE-07 |
| MCP `o11y_` tools / Observability Cloud | IR-03 |
| MCP `es_` tools / Enterprise Security | SO-01, SO-02 (ES also in SO-04, SO-06) |
| MCP `SA-ITOA_` tools / ITSI | IR-04 |
| MCP custom tools | EB-01 |
| splunkctl | IR-01, IR-06, SO-03, SO-04, SO-05, DP-01, DP-02, DP-03, DP-05, DP-06, DP-08, DP-09, DP-10, CE-01 – CE-08, PO-01, PO-03 – PO-12 |
| Agent Skills | All except IR-03, IR-04, IR-05, IR-07, IR-08, SO-01, SO-02, DP-03, PO-11, EB-01, EB-03 (per-skill map in [4.5](#45-agent-skills-coverage)) |
| Agentic SDK (`splunklib.ai`) | IR-07, IR-08, EB-02, EB-03 |
| ACS / Terraform | SO-05, DP-01, DP-10, PO-01, PO-02, PO-08, EB-02 |
| ES / SOAR REST APIs, ES agents, AI Canvas | SO-02, SO-04 |
| Data Management API / Edge & Ingest Processor | DP-04, DP-05, DP-10 |
| Federated Search, Machine Data Lake | SO-03, DP-05 |
| Catalog | DP-07 |
| Agent Launchpad | IR-05 |
| UF / Agent Management (Deployment Server) | DP-06, DP-08 |
| Splunk OTel Collector | DP-02, DP-03, DP-08, DP-10 |
| Ingest Monitoring app | DP-09 |

### 4.3 Third-party technology → use cases

| Role | Technology | Use cases |
|---|---|---|
| Agent client | Any of the six (Interactive mode) | All Interactive rows |
| Agent client | Claude Code / Codex in non-interactive mode | IR-06, CE-04, PO-12 (and any Event or Pipeline row that runs an agent) |
| Model provider | OpenAI, Anthropic, Google, Ollama (via the Agentic SDK) | IR-07, IR-08, EB-03 |
| Trigger | GitHub Actions | IR-06, SO-05, DP-04, DP-10, CE-04, CE-06, PO-01, PO-08, PO-12 |
| Trigger | GitLab CI | SO-05, CE-02, CE-06, PO-08 |
| Trigger | Jenkins | CE-06 |
| Trigger | ArgoCD | IR-03, DP-03 |
| Trigger | cron | SO-06, DP-07, CE-05, PO-10, PO-11, PO-12 |
| Change tooling | Terraform / OpenTofu | DP-10, PO-01, PO-02 |
| Change tooling | Ansible | DP-06, DP-08, PO-04 |
| Change tooling | Helm | DP-03, DP-10 |
| Environment | Kubernetes | IR-03, DP-02, DP-03, DP-10 |
| Environment | AWS | SO-03, DP-05, PO-02, PO-05 |
| Environment | Snowflake, Databricks, Azure | SO-03 |
| Environment | Linux hosts | DP-06, DP-08 |
| Hand-off | Slack / Teams | IR-02, IR-05, IR-06, IR-07, SO-02, DP-09, CE-03 |
| Hand-off | PagerDuty | IR-02, IR-06, DP-09, CE-03 |
| Hand-off | ServiceNow / Jira | IR-02, IR-04, IR-07, SO-02, SO-06, SO-07, PO-10, PO-12 |
| Verification | Playwright | CE-01, CE-02 |

### 4.4 uMELT headless journey coverage

The uMELT headless vision (`umelt_headless_draft.md`) defines its journeys around data administration. Its personas map onto ours: platform/data admin → Splunk Platform Admin; platform engineer → Platform / DevOps Engineer; pipeline/data engineer → Data / Pipeline Engineer; governance owner → Security & Governance Approver; analyst/SRE → SRE and Analyst. uMELT's stated near-term deliverables are API coverage, a Terraform path, and GitOps guidance; a new unified uMELT CLI is explicitly not a priority. uMELT demos should therefore lead with Terraform, GitOps, and agents, and must not imply a uMELT CLI.

| uMELT journey | Use cases | Gap today |
|---|---|---|
| Onboard a use case (umbrella) | DP-10 | No single API across pillars; DP-10 chains separate tools |
| Provision infrastructure | DP-03, DP-10, PO-01 | Splunk side only (indexes, HEC, allowlists); collector hosts are customer Terraform or Helm |
| Enroll and manage the fleet | DP-03, DP-06 | Agent Management REST lists and reloads agents but doesn't enroll new ones; the fleet skill is advisory |
| Connect a source and configure ingestion | DP-01 | Cloud indexes and HEC tokens go through ACS, not splunkctl |
| Configure processing, routing, and landing | DP-04, DP-05 | Data Management API untested; no Terraform provider |
| Set up ingest monitoring | DP-09 | Ingest Monitoring app alerts have no documented API; use saved-search alerts |
| Verify data readiness | DP-07 | — |
| Migrate an existing deployment (UF → collector) | DP-08 | Universal Collector and a UF-to-collector migration path are not publicly documented |
| Manage data lifecycle | DP-05 | Headless path for Machine Data Lake tiering unverified |
| Discover, validate, and investigate data flow | DP-02, DP-07 | — |

### 4.5 Agent Skills coverage

Every one of the 32 skills has a *star* use case: one where that skill does the key work on screen. Many also appear as supporting skills elsewhere.

| Skill | Kind | Star use case | Also in |
|---|---|---|---|
| `alerting-and-notable-workflows` | Advisor | CE-03 | IR-02, DP-09 |
| `app-and-add-on-lifecycle-advisor` | Advisor | PO-08 | PO-04, EB-02 |
| `custom-visualization-builder` | Executor | EB-02 | |
| `dashboard-report-alert-performance-advisor` | Advisor | PO-06 | CE-05 |
| `data-model-and-search-acceleration` | Advisor | CE-04 | SO-04 |
| `data-source-onboarding-advisor` | Advisor | DP-01 | DP-10 |
| `deployment-server-and-forwarder-fleet-management` | Advisor | DP-06 | DP-08 |
| `field-extraction-and-cim-mapping` | Advisor | DP-07 | DP-01, SO-04 |
| `forwarder-and-data-ingest-doctor` | Advisor | DP-02 | DP-08, DP-09, PO-12 |
| `hec-setup-and-troubleshooting` | Executor | DP-02 | DP-01 |
| `incident-diagnosis-specialist` | Advisor | IR-06 | IR-02 |
| `index-and-storage-management-advisor` | Advisor | DP-05 | PO-05 |
| `indexer-cluster-health-and-troubleshooting` | Advisor | PO-03 | |
| `ingestion-pipeline-design` | Advisor | DP-04 | DP-01, DP-10 |
| `knowledge-object-governance` | Advisor | CE-05 | |
| `license-and-capacity-planning-advisor` | Advisor | PO-05 | |
| `report-authoring-specialist` | Advisor | SO-06 | CE-01 |
| `search-and-dashboard-troubleshooter` | Advisor | CE-07 | CE-08 |
| `search-head-cluster-health-and-troubleshooting` | Advisor | PO-03 | |
| `search-performance-optimizer` | Advisor | CE-04 | PO-06 |
| `splunk-cloud-admin-copilot` | Executor | PO-02 | |
| `splunk-dashboard-converter` | Builder | CE-02 | |
| `splunk-enterprise-administration-advisor` | Builder | PO-09 | |
| `splunk-health-monitoring-and-diagnostic-collection` | Advisor | PO-03 | PO-12 |
| `splunk-identity-saml-readiness-advisor` | Executor | PO-09 | PO-07 |
| `splunk-product-question-navigator` | Advisor | PO-04 | Any use case (MCP counterpart: `saia_ask_splunk_question`) |
| `splunk-search` | Executor | IR-01 | IR-06, CE-01, SO-04 |
| `splunk-setup-page-builder` | Builder | EB-02 | |
| `upgrade-and-security-readiness-router` | Advisor | PO-04 | |
| `upgrade-and-vulnerability-readiness-advisor` | Advisor | PO-10 | |
| `upgrade-planning-and-execution-readiness` | Advisor | PO-04 | PO-12 |
| `vulnerability-remediation-and-compliance-readiness` | Advisor | PO-10 | SO-06 |

**Gaps in the skills library.** No skill covers ES detection authoring or ES content packaging, Edge/Ingest Processor (SPL2) pipelines, Observability Cloud, ITSI, or general ACS writes beyond one allowlist CIDR. In those areas (SO-01 – SO-05, DP-04, IR-03, IR-04, PO-08) the Splunk-specific work is done by MCP tools, splunkctl, ACS, or the generic `splunkctl` skill rather than a dedicated Agent Skill.

## 5. Verification notes

Corrections to the drafts in this folder:

- **splunkctl commands.** `splunkctl saved-search disable` does not exist; use `saved-search edit <name> --param disabled=1` (the `disabled` key is confirmed by `--describe`). `splunkctl health list` does not exist; use `server health`. `workload-rule add`, `shcluster-maintenance-mode enable`, `hec send`, and `dashboard add --file` are confirmed.
- **Deployment Server writes.** The use-case draft says fleet changes aren't covered by splunkctl writes. splunkctl does have `serverclass add/edit`, `serverclass clients`, and `forwarder reload` (Enterprise), so DP-06 is possible with caveats.
- **ITSI MCP tools.** Missing from the drafts. ITSI 5.0.1+ registers six read-only `SA-ITOA_` episode tools in the MCP Server.
- **ES MCP scope.** Tool categories also cover response plans, risk scores, and queues. `es_get_ai_analysis` is not available on-premises.
- **ES agents and Detection Studio.** Detection Studio is GA (announced March 2026) and is the supported detection-lifecycle UI. The Triage & Response and Malware Reversing agents require ES Premier; Detection Builder is in Essentials and Premier. These agents run in-product. Headless flows read their output; they don't drive the agents.
- **Edge/Ingest Processor.** Splunk documents a Data Management API for edge processors, pipelines, datasets, and connections, so pipeline-as-code (DP-04) is plausible. No Terraform provider was found. Kept as Emerging until we test it.
- **splunkctl `--read-only` and searches.** The drafts use `splunkctl --read-only search …` for investigation and CI validation. That is rejected: splunkctl gates every non-GET request (`internal/client/client.go`), and search jobs are POSTs. Use `--yes search export` with a read-only token. The README's "investigation runs unattended" holds for GET commands, not for searches.
- **splunkctl can't write saved searches into a specific app.** `saved-search add/edit` has no `--app` flag, and `raw post` always prefixes `/services`, so `/servicesNS/<owner>/<app>/…` is unreachable (`cmd/override/raw.go`). ES detections and app-scoped searches from CI therefore go through a content-app package (ACS `apps install private` on Cloud, `app install` on Enterprise) or direct REST calls. `dashboard add` does support `--app`.
- **ES detections over REST.** ES 8 detections are saved searches with `action.correlationsearch.*` and `action.notable.*` settings, so REST and app-package deployment work. ES records detection version history only for edits made in its detection editor (versioning is on by default from ES 8.4), and there is no public Detection Studio API. A CI pipeline therefore has to keep its own history (Git) and should disclose that ES version history won't reflect pipeline deployments.
- **ACS app automation.** `acs apps install private` runs AppInspect and installs in one step; `acs apps install splunkbase` uses Splunk.com credentials; `acs status current-stack` shows whether a restart is pending. Lantern publishes an ACS starter for GitHub Actions; there is no official GitLab template, but the same commands run in any GitLab runner.
- **uMELT sources.** The uMELT draft is an internal vision. Universal Collector and a UF-to-collector migration path are not publicly documented, Agent Management (the 10.x name for Deployment Server) has REST endpoints for listing and reloading agents but not for enrolling them, and the Ingest Monitoring app's alerts are configured in its UI. DP-08 and DP-10 are Emerging for these reasons.
- **What Agent Skills actually do.** Only 7 of 32 skills may run shell commands, and only 4 call splunkctl (`splunk-search`, `hec-setup-and-troubleshooting`, `splunk-identity-saml-readiness-advisor`, `custom-visualization-builder`). 24 are web-only advisors, and none require MCP. Draft scenarios where an advisory skill "runs" `splunkctl` or "benchmarks SPL" need a separate evidence step (MCP or `splunk-search`).
- **splunkctl skill.** splunkctl ships its own skill (`splunkctl skill install`), separate from the 32 Agent Skills, and only for Claude Code and Codex. It tells the agent to prefer the MCP Server when one is available.
- **Agent Skills list.** All 32 skill names used in this catalog match `splunk/splunk-agent-skills/skills`. The Splunk-named Cursor plugins installed locally (`splunk-dashboards`, `splunk-itsi`, `splunk-cim`, and others) are not part of that repo and have no stated author, so they are excluded from the Splunk-developed list.
- **Agentic SDK release status.** `splunklib.ai` ships in `splunk-sdk` 3.0.0 on PyPI (May 12, 2026, "AI with Splunk Apps"); the current release is 3.0.1 (September 9, 2026). Remote tools come from the MCP Server and must be allowlisted. Local tools live in an app's `bin/tools.py`, so EB-03 runs as a plain script using remote tools only, while IR-07 and IR-08 are packaged as apps. Checked November 16, 2026 against SDK 3.0.1: "plain script" still needs the SDK installed under `$SPLUNK_HOME/etc/apps/<app>/` (`locate_app()` raises otherwise), and the SDK's `GET /services/mcp_token` call returns HTTP 400 on the CO2 MCP Server, so a recorded run supplies the MCP token itself. The captured EB-03 demo uses Gemini on Vertex AI. On Splunk Cloud, AppInspect flags two files from the `openai` dependency; the SDK README documents excluding them at packaging time.
- **Demo-pipeline draft scenarios.** "Karpenter-driven egress", "PR namespace index teardown", and "maintenance mode as part of a CVE audit" are synthetic. They are folded into PO-02, CE-06/PO-01, and PO-04 rather than kept as separate use cases.

Live check of the connected MCP Server (November 15, 2026):

- **Exposed tools:** the same 25 as on November 13: 20 `splunk_` and 5 `saia_`. No `es_`, `o11y_`, or `SA-ITOA_` tools, so SO-01, SO-02, IR-03, and IR-04 can't be recorded on this stack yet.
- **Search concurrency:** `splunk_get_info` and `splunk_get_user_info` were refused at the instance limit (22 of 22 concurrent historical searches), and `splunk_get_indexes` hit the 60-second timeout. Most MCP tools run as searches, so agent traffic competes with scheduled searches. This supports a dedicated workload pool (PO-07) and makes a good live hook for PO-06.
- **AI Assistant:** `saia_generate_spl` still returns "Service not initialized".

Reusable demo material found in the repos:

- `splunkctl/DEMO.md`: a prompt-by-prompt Claude Code script covering health, search, indexes, users, HEC, saved searches, dashboards, KV Store, config, license, and raw REST, including the `CONFIRMATION_REQUIRED` approval etiquette.
- `skills/*/agents/openai.yaml`: a display name, short description, and default prompt for every skill. Useful as scenario titles and opening prompts.
- `skills/splunk-dashboard-converter/evals.json`: evaluation cases that can double as CE-02 demo inputs.

Open items to verify before external use:

- Which splunkctl write commands succeed on Splunk Cloud Platform versus requiring ACS (affects DP-01, CE-01 – CE-06 on Cloud).
- A demo stack with `es_`, `o11y_`, and ITSI tools enabled, AI Assistant provisioned, and spare search concurrency (or a workload pool for MCP).
- Data Management API coverage for creating and applying pipelines (DP-04).
- Headless access path for Machine Data Lake and Catalog beyond SPL2 search (DP-05, DP-07).