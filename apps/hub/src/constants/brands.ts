import azure from '@/assets/brands/azure.svg'
import claude from '@/assets/brands/claude.svg'
import cursor from '@/assets/brands/cursor.svg'
import geminiCli from '@/assets/brands/gemini-cli.svg'
import gemini from '@/assets/brands/gemini.svg'
import githubActions from '@/assets/brands/github-actions.svg'
import githubCopilot from '@/assets/brands/github-copilot.svg'
import jira from '@/assets/brands/jira.svg'
import kubernetes from '@/assets/brands/kubernetes.svg'
import n8n from '@/assets/brands/n8n.svg'
import openai from '@/assets/brands/openai.svg'
import outlook from '@/assets/brands/outlook.svg'
import playwright from '@/assets/brands/playwright.svg'
import python from '@/assets/brands/python.svg'
import slack from '@/assets/brands/slack.svg'
import terraform from '@/assets/brands/terraform.svg'

/**
 * Logo for each third-party agent and technology tag, keyed by its vocabulary value in taxonomy.ts.
 * Decorative: the tag text always names the product. Sources and licenses: assets/brands/README.md.
 */
export const BRAND_ICON: Record<string, string> = {
  // Claude Code shows the Claude app mark; Codex shows its maker's, OpenAI.
  Azure: azure,
  'Claude Code': claude,
  Codex: openai,
  Cursor: cursor,
  'Gemini CLI': geminiCli,
  Gemini: gemini,
  'GitHub Actions': githubActions,
  'GitHub Copilot': githubCopilot,
  Jira: jira,
  Kubernetes: kubernetes,
  n8n: n8n,
  Outlook: outlook,
  Playwright: playwright,
  Python: python,
  Slack: slack,
  Terraform: terraform,
}
