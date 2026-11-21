import { workflow, node, trigger, merge, newCredential, expr } from '@n8n/workflow-sdk';

const containmentRequest = trigger({
  type: 'n8n-nodes-base.webhook',
  version: 2.1,
  config: {
    name: 'Start containment',
    position: [0, 210],
    parameters: {
      httpMethod: 'POST',
      path: 'contain-phishing',
      authentication: 'headerAuth',
      responseMode: 'lastNode',
      responseData: 'firstEntryJson'
    },
    credentials: { httpHeaderAuth: newCredential('Cursor CLI webhook') }
  },
  output: [{ body: { case_id: 'PH-1042', internet_message_id: '<88213.ap-notices@northwind-billing.example>', sender_domain: 'northwind-billing.example', recipients: ['mark.chen@acme-corp.example'] } }]
});

const purgeEmail = node({
  type: 'n8n-nodes-base.httpRequest',
  version: 4.3,
  config: {
    name: 'Purge email from inboxes',
    position: [280, 120],
    parameters: {
      method: 'POST',
      url: 'https://splunk-hec.example.com/services/collector/event',
      authentication: 'genericCredentialType',
      genericAuthType: 'httpHeaderAuth',
      sendBody: true,
      contentType: 'raw',
      // HEC takes newline-separated events; declared as JSON, n8n would re-encode a multi-event body as one string.
      rawContentType: 'text/plain',
      body: expr("{{ $json.body.recipients.map(r => JSON.stringify({ sourcetype: 'containment:audit', source: 'n8n', event: { case_id: $json.body.case_id, action: 'message_purged', system: 'mail', target: r, internet_message_id: $json.body.internet_message_id, execution_id: $execution.id } })).join('\\n') }}")
    },
    credentials: { httpHeaderAuth: newCredential('Splunk HEC (demo)') }
  },
  output: [{ text: 'Success', code: 0 }]
});

const blockDomain = node({
  type: 'n8n-nodes-base.httpRequest',
  version: 4.3,
  config: {
    name: 'Block sender domain',
    position: [280, 300],
    parameters: {
      method: 'POST',
      url: 'https://splunk-hec.example.com/services/collector/event',
      authentication: 'genericCredentialType',
      genericAuthType: 'httpHeaderAuth',
      sendBody: true,
      contentType: 'raw',
      rawContentType: 'text/plain',
      body: expr("{{ JSON.stringify({ sourcetype: 'containment:audit', source: 'n8n', event: { case_id: $json.body.case_id, action: 'domain_blocked', system: 'mail-gateway', target: $json.body.sender_domain, execution_id: $execution.id } }) }}")
    },
    credentials: { httpHeaderAuth: newCredential('Splunk HEC (demo)') }
  },
  output: [{ text: 'Success', code: 0 }]
});

const waitForResults = merge({
  version: 3.2,
  config: {
    name: 'Wait for results',
    position: [560, 210],
    parameters: { mode: 'append', numberInputs: 2 }
  }
});

const notifyAnalyst = node({
  type: 'n8n-nodes-base.slack',
  version: 2.3,
  config: {
    name: 'Notify analyst in Slack',
    position: [820, 210],
    executeOnce: true,
    parameters: {
      resource: 'message',
      operation: 'post',
      authentication: 'accessToken',
      select: 'channel',
      // The workspace's channel ID stays out of the repo; pick #phishing-response in n8n.
      channelId: { __rl: true, mode: 'id', value: 'C00000000000', cachedResultName: 'phishing-response' },
      messageType: 'text',
      text: expr(":white_check_mark: *Phishing containment done* for case {{ $('Start containment').item.json.body.case_id }}\n• Purged the email from {{ $('Start containment').item.json.body.recipients.length }} inboxes\n• Blocked {{ $('Start containment').item.json.body.sender_domain }}\nAsk Cursor to verify the result in Splunk."),
      otherOptions: { includeLinkToWorkflow: false }
    },
    credentials: { slackApi: newCredential('Slack SOC Automation bot') }
  },
  output: [{ ok: true, channel: 'C00000000000', ts: '1795190000.000100' }]
});

export default workflow('closed-loop-phishing-containment', 'Closed-loop phishing containment')
  .add(containmentRequest)
  .to(purgeEmail.to(waitForResults.input(0)))
  .add(containmentRequest)
  .to(blockDomain.to(waitForResults.input(1)))
  .add(waitForResults)
  .to(notifyAnalyst);
