interface BoxProps {
  x: number
  y: number
  w: number
  h: number
  title: string
  sub: string
  stroke: string
  dashed?: boolean
  note?: string
}

function Box({ x, y, w, h, title, sub, stroke, dashed, note }: BoxProps) {
  return (
    <g>
      <rect
        x={x}
        y={y}
        width={w}
        height={h}
        rx={8}
        fill="var(--surface-card)"
        stroke={stroke}
        strokeWidth={1.3}
        strokeDasharray={dashed ? '4 3' : undefined}
      />
      <text x={x + 14} y={y + 25} fontSize={13.5} fontWeight={600} fill="var(--text-primary)">
        {title}
      </text>
      <text x={x + 14} y={y + 44} fontSize={11.5} fill="var(--text-secondary)">
        {sub}
      </text>
      {note && (
        <text x={x + 14} y={y + 62} fontSize={11} fill="var(--status-warning)">
          {note}
        </text>
      )}
    </g>
  )
}

function Label({ x, y, children, warn }: { x: number; y: number; children: string; warn?: boolean }) {
  return (
    <text x={x} y={y} fontSize={11} textAnchor="middle" fill={warn ? 'var(--status-warning)' : 'var(--text-muted)'}>
      {children}
    </text>
  )
}

// Columns: You 0–116 · agent 180–350 · tools 410–670 · Splunk 750–890. Tool boxes are 260 wide so the
// splunkctl note fits; widen a column before lengthening any label in it.
export function FlowDiagram({ browser = true, mcp = 'MCP · sourcetypes, SPL' }: { browser?: boolean; mcp?: string }) {
  return (
    <svg viewBox={`0 0 900 ${browser ? 300 : 204}`} className="h-auto w-full font-sans" role="img" aria-labelledby="flow-title flow-desc">
      <title id="flow-title">How the pieces fit together</title>
      <desc id="flow-desc">
        You prompt Cursor CLI, guided by Agent Skills. Cursor CLI uses splunkctl over REST port 8089, where writes stop at
        CONFIRMATION_REQUIRED and Cursor asks you first{browser ? '; Splunk MCP for sourcetypes and SPL; and Playwright CLI to open the dashboard in Splunk Web' : ', and Splunk MCP to run searches'}.
      </desc>
      <defs>
        <marker id="flow-arrow" viewBox="0 0 8 8" refX={7} refY={4} markerWidth={7} markerHeight={7} orient="auto">
          <path d="M0 0L8 4L0 8z" fill="var(--text-muted)" />
        </marker>
        <marker id="flow-arrow-warn" viewBox="0 0 8 8" refX={7} refY={4} markerWidth={7} markerHeight={7} orient="auto">
          <path d="M0 0L8 4L0 8z" fill="var(--status-warning)" />
        </marker>
      </defs>
      <Box x={0} y={112} w={116} h={76} title="You" sub="prompt, approve" stroke="var(--border-strong)" />
      <Box x={180} y={18} w={170} h={58} title="Agent Skills" sub="how to search and build" stroke="var(--border-default)" dashed />
      <Box x={180} y={112} w={170} h={76} title="Cursor CLI" sub="the agent" stroke="var(--text-primary)" />
      <Box
        x={410}
        y={18}
        w={260}
        h={76}
        title="splunkctl"
        sub="Shell"
        stroke="var(--status-success)"
        note="writes stop at CONFIRMATION_REQUIRED"
      />
      <Box x={410} y={116} w={260} h={68} title="Splunk MCP" sub={mcp} stroke="var(--action-primary)" />
      {browser && (
        <Box x={410} y={206} w={260} h={68} title="Playwright CLI" sub="Shell · open, check panels" stroke="var(--status-info)" />
      )}
      <Box x={750} y={18} w={140} h={166} title="Splunk Cloud" sub="REST and MCP" stroke="var(--border-strong)" />
      {browser && <Box x={750} y={206} w={140} h={68} title="Splunk Web" sub="the dashboard" stroke="var(--border-strong)" />}
      <g stroke="var(--text-muted)" strokeWidth={1.3} fill="none" markerEnd="url(#flow-arrow)">
        <path d="M116 138H178" />
        <path d="M265 76V110" />
        <path d="M350 150C380 150 380 56 408 56" />
        <path d="M350 150H408" />
        {browser && <path d="M350 150C380 150 380 240 408 240" />}
        <path d="M670 56H748" />
        <path d="M670 150H748" />
        {browser && <path d="M670 240H748" />}
      </g>
      <path d="M178 164H118" stroke="var(--status-warning)" strokeWidth={1.3} strokeDasharray="4 3" fill="none" markerEnd="url(#flow-arrow-warn)" />
      <Label x={147} y={130}>prompt</Label>
      <Label x={147} y={182} warn>
        asks first
      </Label>
      <text x={273} y={97} fontSize={11} fill="var(--text-muted)">
        guides
      </text>
      <Label x={709} y={48}>REST :8089</Label>
      <Label x={709} y={142}>MCP</Label>
      {browser && <Label x={709} y={232}>HTTPS</Label>}
    </svg>
  )
}

// Same columns as FlowDiagram, one more row. The loop: Splunk finds the threat, n8n acts after approval and writes
// its audit records back to Splunk, Slack tells you, and the same agent proves the fix in Splunk.
/** The closed-loop phishing story: Outlook report, Agent Launchpad triage, approved n8n containment, Slack, verify. */
export function PhishingFlowDiagram() {
  return (
    <svg viewBox="0 0 900 380" className="h-auto w-full font-sans" role="img" aria-labelledby="phish-flow-title phish-flow-desc">
      <title id="phish-flow-title">How the pieces fit together</title>
      <desc id="phish-flow-desc">
        You prompt Cursor CLI. It reads the reported email from Outlook through the Outlook MCP, and runs the Agent Launchpad
        triage agent in Splunk Cloud with splunkctl. Containment goes through n8n-contain, which stops at
        CONFIRMATION_REQUIRED, so Cursor asks you first. After approval, n8n purges the email and blocks the domain, writes
        the audit records to Splunk over HEC, and tells you in Slack. The same agent then verifies the containment in Splunk.
      </desc>
      <defs>
        <marker id="phish-flow-arrow" viewBox="0 0 8 8" refX={7} refY={4} markerWidth={7} markerHeight={7} orient="auto">
          <path d="M0 0L8 4L0 8z" fill="var(--text-muted)" />
        </marker>
        <marker id="phish-flow-arrow-warn" viewBox="0 0 8 8" refX={7} refY={4} markerWidth={7} markerHeight={7} orient="auto">
          <path d="M0 0L8 4L0 8z" fill="var(--status-warning)" />
        </marker>
      </defs>
      <Box x={0} y={112} w={116} h={76} title="You" sub="prompt, approve" stroke="var(--border-strong)" />
      <Box x={180} y={112} w={170} h={76} title="Cursor CLI" sub="the agent" stroke="var(--text-primary)" />
      <Box x={410} y={18} w={260} h={68} title="Outlook MCP" sub="read the reported email" stroke="var(--status-info)" />
      <Box x={410} y={112} w={260} h={76} title="splunkctl" sub="Shell · run the Launchpad agent" stroke="var(--action-primary)" />
      <Box
        x={410}
        y={214}
        w={260}
        h={76}
        title="n8n-contain"
        sub="Shell · start containment"
        stroke="var(--status-success)"
        note="stops at CONFIRMATION_REQUIRED"
      />
      <Box x={750} y={18} w={140} h={68} title="Outlook" sub="Phishing reports" stroke="var(--border-strong)" />
      <Box x={750} y={112} w={140} h={76} title="Splunk Cloud" sub="Agent Launchpad" stroke="var(--border-strong)" note="triage, verify" />
      <Box x={750} y={214} w={140} h={76} title="n8n" sub="purge, block" stroke="var(--border-strong)" />
      <Box x={750} y={314} w={140} h={56} title="Slack" sub="#phishing-response" stroke="var(--border-strong)" />
      <g stroke="var(--text-muted)" strokeWidth={1.3} fill="none" markerEnd="url(#phish-flow-arrow)">
        <path d="M116 138H178" />
        <path d="M350 150C380 150 380 52 408 52" />
        <path d="M350 150H408" />
        <path d="M350 150C380 150 380 252 408 252" />
        <path d="M670 52H748" />
        <path d="M670 150H748" />
        <path d="M670 252H748" />
        <path d="M820 214V190" />
        <path d="M820 290V312" />
        <path d="M750 342H58V190" />
      </g>
      <path d="M178 164H118" stroke="var(--status-warning)" strokeWidth={1.3} strokeDasharray="4 3" fill="none" markerEnd="url(#phish-flow-arrow-warn)" />
      <Label x={147} y={130}>prompt</Label>
      <Label x={147} y={182} warn>
        asks first
      </Label>
      <Label x={709} y={44}>MCP</Label>
      <Label x={709} y={142}>aiagent</Label>
      <Label x={709} y={244}>webhook</Label>
      <text x={828} y={206} fontSize={11} fill="var(--text-muted)">
        audit (HEC)
      </text>
      <Label x={404} y={334}>tells you it's done</Label>
    </svg>
  )
}

// Same columns as FlowDiagram. Jira writes go through acli, which holds them for approval; both MCP servers only read.
/** The Jira hand-off story: alerts come from Jira, evidence from Splunk, and the follow-up ticket waits for you. */
export function JiraFlowDiagram({ mcp = 'searches, saved ML models' }: { mcp?: string }) {
  return (
    <svg viewBox="0 0 900 300" className="h-auto w-full font-sans" role="img" aria-labelledby="jira-flow-title jira-flow-desc">
      <title id="jira-flow-title">How the pieces fit together</title>
      <desc id="jira-flow-desc">
        You prompt Cursor CLI. It reads alerts from Jira Cloud through the Atlassian MCP, and searches Splunk Cloud and applies
        AI Toolkit models through Splunk MCP. Its only way to write to Jira is acli, which stops at CONFIRMATION_REQUIRED, so
        Cursor asks you first.
      </desc>
      <defs>
        <marker id="jira-flow-arrow" viewBox="0 0 8 8" refX={7} refY={4} markerWidth={7} markerHeight={7} orient="auto">
          <path d="M0 0L8 4L0 8z" fill="var(--text-muted)" />
        </marker>
        <marker id="jira-flow-arrow-warn" viewBox="0 0 8 8" refX={7} refY={4} markerWidth={7} markerHeight={7} orient="auto">
          <path d="M0 0L8 4L0 8z" fill="var(--status-warning)" />
        </marker>
      </defs>
      <Box x={0} y={112} w={116} h={76} title="You" sub="prompt, approve" stroke="var(--border-strong)" />
      <Box x={180} y={112} w={170} h={76} title="Cursor CLI" sub="the agent" stroke="var(--text-primary)" />
      <Box
        x={410}
        y={18}
        w={260}
        h={76}
        title="acli"
        sub="Shell · the follow-up ticket"
        stroke="var(--status-success)"
        note="writes stop at CONFIRMATION_REQUIRED"
      />
      <Box x={410} y={116} w={260} h={68} title="Atlassian MCP" sub="read alerts" stroke="var(--status-info)" />
      <Box x={410} y={206} w={260} h={68} title="Splunk MCP" sub={mcp} stroke="var(--action-primary)" />
      <Box x={750} y={18} w={140} h={166} title="Jira Cloud" sub="alerts and tickets" stroke="var(--border-strong)" />
      <Box x={750} y={206} w={140} h={68} title="Splunk Cloud" sub="AI Toolkit" stroke="var(--border-strong)" />
      <g stroke="var(--text-muted)" strokeWidth={1.3} fill="none" markerEnd="url(#jira-flow-arrow)">
        <path d="M116 138H178" />
        <path d="M350 150C380 150 380 56 408 56" />
        <path d="M350 150H408" />
        <path d="M350 150C380 150 380 240 408 240" />
        <path d="M670 56H748" />
        <path d="M670 150H748" />
        <path d="M670 240H748" />
      </g>
      <path d="M178 164H118" stroke="var(--status-warning)" strokeWidth={1.3} strokeDasharray="4 3" fill="none" markerEnd="url(#jira-flow-arrow-warn)" />
      <Label x={147} y={130}>prompt</Label>
      <Label x={147} y={182} warn>
        asks first
      </Label>
      <Label x={709} y={48}>REST</Label>
      <Label x={709} y={142}>MCP</Label>
      <Label x={709} y={232}>MCP</Label>
    </svg>
  )
}

// Columns: You 0–100 · Cursor CLI 164–280 · tools 330–580 · Splunk Cloud 640–900, with the AI Toolkit inside it and the
// self-hosted model below. Tool boxes are 250 wide so the splunkctl note fits.
/** The CDTSM story: the agent runs the AI Toolkit's CDTSM through Splunk MCP, and the model is served from Azure. */
export function CdtsmFlowDiagram({ mcp = 'search, apply CDTSM' }: { mcp?: string }) {
  return (
    <svg viewBox="0 0 900 300" className="h-auto w-full font-sans" role="img" aria-labelledby="cdtsm-flow-title cdtsm-flow-desc">
      <title id="cdtsm-flow-title">How the pieces fit together</title>
      <desc id="cdtsm-flow-desc">
        You prompt Cursor CLI. It searches Splunk Cloud through Splunk MCP and runs apply CDTSM, the Splunk AI Toolkit command that
        sends each time series to the Cisco Deep Time Series Model, self-hosted on Azure Container Apps. It creates the alert with
        splunkctl over REST port 8089, where the write stops at CONFIRMATION_REQUIRED and Cursor asks you first.
      </desc>
      <defs>
        <marker id="cdtsm-flow-arrow" viewBox="0 0 8 8" refX={7} refY={4} markerWidth={7} markerHeight={7} orient="auto">
          <path d="M0 0L8 4L0 8z" fill="var(--text-muted)" />
        </marker>
        <marker id="cdtsm-flow-arrow-warn" viewBox="0 0 8 8" refX={7} refY={4} markerWidth={7} markerHeight={7} orient="auto">
          <path d="M0 0L8 4L0 8z" fill="var(--status-warning)" />
        </marker>
      </defs>
      <Box x={0} y={112} w={100} h={76} title="You" sub="prompt, approve" stroke="var(--border-strong)" />
      <Box x={164} y={112} w={116} h={76} title="Cursor CLI" sub="the agent" stroke="var(--text-primary)" />
      <Box
        x={330}
        y={18}
        w={250}
        h={76}
        title="splunkctl"
        sub="Shell · create the alert"
        stroke="var(--status-success)"
        note="writes stop at CONFIRMATION_REQUIRED"
      />
      <Box x={330} y={116} w={250} h={68} title="Splunk MCP" sub={mcp} stroke="var(--action-primary)" />
      <Box x={640} y={18} w={260} h={166} title="Splunk Cloud" sub="REST :8089 and MCP" stroke="var(--border-strong)" />
      <Box x={656} y={96} w={228} h={72} title="Splunk AI Toolkit" sub="apply CDTSM, the alert search" stroke="var(--action-primary)" />
      <Box
        x={640}
        y={214}
        w={260}
        h={72}
        title="Cisco Deep Time Series Model"
        sub="CDTSM · Azure Container Apps"
        stroke="var(--status-info)"
        dashed
      />
      <g stroke="var(--text-muted)" strokeWidth={1.3} fill="none" markerEnd="url(#cdtsm-flow-arrow)">
        <path d="M100 138H162" />
        <path d="M280 150C305 150 305 56 328 56" />
        <path d="M280 150H328" />
        <path d="M580 56H638" />
        <path d="M580 150H654" />
        <path d="M770 168V212" />
      </g>
      <path d="M162 164H102" stroke="var(--status-warning)" strokeWidth={1.3} strokeDasharray="4 3" fill="none" markerEnd="url(#cdtsm-flow-arrow-warn)" />
      <Label x={132} y={130}>prompt</Label>
      <Label x={132} y={182} warn>
        asks first
      </Label>
      <Label x={609} y={48}>REST</Label>
      <Label x={609} y={142}>MCP</Label>
      <text x={780} y={195} fontSize={11} fill="var(--text-muted)">
        HTTPS · bearer token
      </text>
    </svg>
  )
}

// Columns: You 0–100 · Cursor CLI 140–280 · agent.py 320–490 · model and tools 540–720 · Splunk 770–900.
/** The Agentic SDK story: Cursor writes a script, and the script is the agent. No splunkctl, no approval. */
export function SdkFlowDiagram({ mcp = '2 allowlisted tools' }: { mcp?: string }) {
  return (
    <svg viewBox="0 0 900 204" className="h-auto w-full font-sans" role="img" aria-labelledby="sdk-flow-title sdk-flow-desc">
      <title id="sdk-flow-title">How the pieces fit together</title>
      <desc id="sdk-flow-desc">
        You prompt Cursor CLI, which writes and runs agent.py. The script uses the Splunk Agentic SDK to send the question to a
        Gemini model on Vertex AI, which can call only the allowlisted Splunk MCP Server tools. Those tools read from Splunk Cloud,
        and the script prints structured output.
      </desc>
      <defs>
        <marker id="sdk-flow-arrow" viewBox="0 0 8 8" refX={7} refY={4} markerWidth={7} markerHeight={7} orient="auto">
          <path d="M0 0L8 4L0 8z" fill="var(--text-muted)" />
        </marker>
      </defs>
      <Box x={0} y={112} w={100} h={76} title="You" sub="prompt" stroke="var(--border-strong)" />
      <Box x={140} y={112} w={140} h={76} title="Cursor CLI" sub="writes and runs" stroke="var(--text-primary)" />
      <Box x={320} y={112} w={170} h={76} title="agent.py" sub="Agentic SDK · ~30 lines" stroke="var(--status-success)" />
      <Box x={540} y={18} w={180} h={76} title="Gemini" sub="model · Vertex AI" stroke="var(--status-info)" />
      <Box x={540} y={112} w={180} h={76} title="Splunk MCP Server" sub={mcp} stroke="var(--action-primary)" />
      <Box x={770} y={112} w={130} h={76} title="Splunk Cloud" sub="REST :8089" stroke="var(--border-strong)" />
      <g stroke="var(--text-muted)" strokeWidth={1.3} fill="none" markerEnd="url(#sdk-flow-arrow)">
        <path d="M100 150H138" />
        <path d="M280 150H318" />
        <path d="M490 150C515 150 515 56 538 56" />
        <path d="M490 150H538" />
        <path d="M720 150H768" />
      </g>
      <Label x={119} y={142}>prompt</Label>
      <Label x={299} y={142}>file</Label>
      <Label x={745} y={142}>read</Label>
    </svg>
  )
}

// Columns: You 0–100 · Cursor CLI 150–280 · tools 340–600 · Splunk Cloud 660–900, with the Machine Data Lake inside it.
// The kernel box is dashed-green like the other gated tools; the notebook file sits under it.
/** The notebook story: the agent runs notebook cells through jpterm, each one held for approval, and one cell reads the lake. */
export function NotebookFlowDiagram({ mcp = 'hot index, triage' }: { mcp?: string }) {
  return (
    <svg viewBox="0 0 900 300" className="h-auto w-full font-sans" role="img" aria-labelledby="nb-flow-title nb-flow-desc">
      <title id="nb-flow-title">How the pieces fit together</title>
      <desc id="nb-flow-desc">
        You prompt Cursor CLI. It triages the hot index through Splunk MCP, then works through a Jupyter notebook with jpterm.
        Each cell the kernel runs stops at CONFIRMATION_REQUIRED, so Cursor asks you first. The approved cells search the Machine
        Data Lake, load a shared table into the kernel, and backtest the detection over 90 days.
      </desc>
      <defs>
        <marker id="nb-flow-arrow" viewBox="0 0 8 8" refX={7} refY={4} markerWidth={7} markerHeight={7} orient="auto">
          <path d="M0 0L8 4L0 8z" fill="var(--text-muted)" />
        </marker>
        <marker id="nb-flow-arrow-warn" viewBox="0 0 8 8" refX={7} refY={4} markerWidth={7} markerHeight={7} orient="auto">
          <path d="M0 0L8 4L0 8z" fill="var(--status-warning)" />
        </marker>
      </defs>
      <Box x={0} y={112} w={100} h={76} title="You" sub="prompt, approve" stroke="var(--border-strong)" />
      <Box x={150} y={112} w={130} h={76} title="Cursor CLI" sub="the agent" stroke="var(--text-primary)" />
      <Box
        x={340}
        y={18}
        w={260}
        h={76}
        title="jpterm"
        sub="Shell · run notebook cells"
        stroke="var(--status-success)"
        note="each cell stops at CONFIRMATION_REQUIRED"
      />
      <Box x={340} y={112} w={260} h={68} title="Jupyter kernel" sub="hunt.ipynb · Python, pandas" stroke="var(--status-info)" />
      <Box x={340} y={206} w={260} h={68} title="Splunk MCP" sub={mcp} stroke="var(--action-primary)" />
      <Box x={660} y={18} w={240} h={256} title="Splunk Cloud" sub="search head, MCP" stroke="var(--border-strong)" />
      <Box x={676} y={104} w={208} h={80} title="Machine Data Lake" sub="raw table · shared table" stroke="var(--action-primary)" />
      <g stroke="var(--text-muted)" strokeWidth={1.3} fill="none" markerEnd="url(#nb-flow-arrow)">
        <path d="M100 138H148" />
        <path d="M280 150C310 150 310 56 338 56" />
        <path d="M280 150C310 150 310 240 338 240" />
        <path d="M470 94V110" />
        <path d="M600 146H674" />
        <path d="M600 240H658" />
      </g>
      <path d="M148 164H102" stroke="var(--status-warning)" strokeWidth={1.3} strokeDasharray="4 3" fill="none" markerEnd="url(#nb-flow-arrow-warn)" />
      <Label x={125} y={130}>prompt</Label>
      <Label x={125} y={182} warn>
        asks first
      </Label>
      <Label x={632} y={138}>reads</Label>
      <Label x={630} y={232}>MCP</Label>
    </svg>
  )
}
