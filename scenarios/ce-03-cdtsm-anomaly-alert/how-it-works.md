## About

Customers say checkout felt slow in Europe this morning, but no alert fired. The latency alert uses one fixed threshold, and checkout latency rises and falls with daily traffic. Set the threshold low and it fires every afternoon. Set it high and it misses a real slowdown in one region.

In this demo an SRE asks Cursor CLI to check the last 24 hours with the Cisco Deep Time Series Model, a pretrained model in the Splunk AI Toolkit. The model forecasts what each region's p95 latency should be at every moment, and flags the stretches where the real line leaves the forecast band. It needs no training. It finds one anomaly: about two hours in eu-west-1, peaking around four times the expected latency. The other regions stay inside their bands.

The SRE then asks for an alert that runs the same check every 15 minutes. The agent drafts it, and splunkctl holds the create until you approve. The next slowdown pages someone, and the threshold follows the daily rhythm on its own.

### What it uses

The Cisco Deep Time Series Model runs behind the AI Toolkit's `apply CDTSM` command. Here it is served from a self-hosted container on Azure. Splunk MCP lets the agent run it without changing anything. splunkctl is the only way the agent can create the alert, and it waits for your approval first. The checkout data is synthetic.

### Prerequisites

- **Splunk Cloud** stack with the **Splunk AI Toolkit** 5.7.3 or later
- **Cisco Deep Time Series Model** endpoint, hosted by Splunk or self-hosted
- **Splunk MCP** app and an MCP token
- **splunkctl** 0.1.2 or later, with a token
- **Cursor CLI**

### Learn more

- [Cisco Deep Time Series Model (Splunk AI Toolkit docs)](https://help.splunk.com/en/splunk-cloud-platform/apply-machine-learning/use-ai-toolkit/6.2.0/ai-toolkit-models/cisco-deep-time-series-model)
- [Splunk MCP on Splunkbase](https://splunkbase.splunk.com/app/7931)
- [splunkctl on GitHub](https://github.com/splunk/splunkctl)
