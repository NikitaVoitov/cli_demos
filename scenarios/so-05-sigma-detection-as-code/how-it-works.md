## About

Attackers such as Volt Typhoon dump LSASS memory with `comsvcs.dll`, a DLL that ships with Windows. Splunk's ESCU has a rule for it, but out-of-the-box content rarely fits every environment as is: this one is off, and it misses other ways of calling the same function. Detection engineers need to adapt content like this quickly, without skipping review and testing.

This demo shows detection refactoring as an agentic workflow built on detection-as-code practices. GitHub Copilot CLI finds the coverage gap through Splunk MCP, turns SigmaHQ's community rule into an Enterprise Security detection with tests, and opens a pull request. GitHub Actions proves it against real attack data and a week of endpoint events, and Splunk AI Toolkit triages the noise so the agent can tune it the way the team already does.

The engineer stays in control. Detections live in Git, CI checks every change, and nothing reaches Enterprise Security until a person approves the merge; then the pipeline deploys it and Splunk confirms it is live. The endpoint week and the ordinal variants are generated for the demo; the attack events come from Splunk's attack_data.

### What it uses

- **Sigma and sigma-cli** with the Splunk backend: one community rule, converted to a `tstats` search on the CIM Endpoint data model.
- **contentctl**, the open-source tool the Splunk Threat Research Team used to build ESCU: it validates the detection YAML and packages the ES app. Splunk is bringing detection-as-code into Detection Studio.
- **GitHub Actions**: a `validate` workflow on every pull request (Sigma lint, drift check, contentctl build, replayed tests, ESCU comparison, noise check, AI triage) and a `deploy` workflow on merge that installs the detections over the Splunk REST API and removes any no longer in the repo.
- **Splunk AI Toolkit**: the `ai` search command with the team's own Azure OpenAI connection triages the noise inside Splunk.
- **Splunk MCP**: Copilot's read-only view of ES detections and searches.
- **GitHub Copilot CLI** with a `gh` wrapper that holds `gh pr merge` until `--yes`.

### Prerequisites

- **Splunk Cloud** with **Enterprise Security 8**, **ESCU**, the **Splunk Add-on for Sysmon**, and the **CIM**
- **Splunk MCP** app and an MCP token; **AI Toolkit** with an LLM connection
- A test index and an HEC token for it; a read-only search token and a deploy token for CI
- A GitHub repository with Actions, **contentctl**, **sigma-cli** with **pySigma-backend-splunk**
- **GitHub Copilot CLI**

### Learn more

- [What is detection as code?](https://www.splunk.com/en_us/blog/learn/detection-as-code.html)
- [Using contentctl to speed up your SOC](https://lantern.splunk.com/Security_Use_Cases/Security_Monitoring/Using_contentctl_to_speed_up_your_SOC)
- [Sigma: getting started](https://sigmahq.io/docs/guide/getting-started.html)
- [contentctl](https://github.com/splunk/contentctl) and its [sample CI/CD templates](https://github.com/splunk/contentctl/blob/main/docs/Sample_CICD_Templates.md)
- [Splunk attack_data](https://github.com/splunk/attack_data)
- [About the ai command](https://help.splunk.com/en/splunk-cloud-platform/apply-machine-learning/use-ai-toolkit/6.3.0/ai-toolkit-commands-macros-and-visualizations/about-the-ai-command)
- [Detection Studio](https://www.splunk.com/en_us/products/detection-studio.html)
- [GitHub Copilot CLI](https://docs.github.com/en/copilot/concepts/agents/about-copilot-cli)
