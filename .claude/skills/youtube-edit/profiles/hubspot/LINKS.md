# HubSpot link library (YouTube descriptions, pinned comments)

The youtube stage takes links from here. A link that isn't here goes in only after the run opens the page and it
resolves; it's then marked `verified` in metadata.json and listed under "For you" so it can be added here. Never a
link from memory. `opened` = the page was opened and read on that date; `linked` = linked from an official HubSpot page
opened that day. Ids are what metadata.json uses (`{link:<id>}`). YouTube links get no UTM.

| Id | Label | URL | Use it for | Checked |
| --- | --- | --- | --- | --- |
| headless-landing | HubSpot MCP server: connect your AI tools | https://developers.hubspot.com/ai-tools/mcp | the HubSpot Is Going Headless series landing page (every video in the series) | opened 2026-11-24 |
| headless-blog | HubSpot's CRM is going headless: choose your own adventure (blog, Brooke Bond) | https://developers.hubspot.com/blog/hubspots-crm-is-going-headless-now-choose-your-own-adventure | the written walkthrough of the series, agents and the Agent CLI (every video in the series) | **not live: 404 on 2026-11-24.** Open it again before use; leave it out while it does not resolve |
| claude-connector | HubSpot connector for Claude | https://www.hubspot.com/claude/connector | any video that uses HubSpot in Claude | opened 2026-11-23 |
| claude-directory | Install the HubSpot connector in Claude | https://claude.ai/directory/connectors/hubspot | a direct install link next to claude-connector | linked 2026-11-23 |
| ai-connectors | HubSpot AI connectors (Claude, ChatGPT, Copilot, Gemini) | https://www.hubspot.com/ai-tools | videos that apply to more than one AI tool | linked 2026-11-23 |
| mcp-server-docs | Using the HubSpot MCP server (docs) | https://developers.hubspot.com/docs/build-with-ai/remote-mcp-server | connectors, agents acting on CRM data | opened 2026-11-23 |
| mcp-integrate-docs | Integrate AI tools with the HubSpot MCP server | https://developers.hubspot.com/docs/apps/developer-platform/build-apps/integrate-with-hubspot-mcp-server | building your own MCP connector | linked 2026-11-23 |
| dev-mcp-docs | HubSpot Developer MCP server | https://developers.hubspot.com/docs/build-with-ai/developer-mcp-server | coding agents building on the developer platform | linked 2026-11-23 |
| agent-cli-docs | HubSpot Agent CLI guide | https://developers.hubspot.com/docs/developer-tooling/local-development/agent-cli/guide | the Agent CLI | linked 2026-11-23 |
| agent-cli-changelog | Agent CLI public beta (changelog) | https://developers.hubspot.com/changelog/hubspot-agent-cli-available-in-public-beta | the Agent CLI announcement | opened 2026-11-23 |
| agent-cli-blog | Introducing the HubSpot Agent CLI | https://blog.hubspot.com/marketing/introducing-the-hubspot-agent-cli | why the Agent CLI exists, use cases | linked 2026-11-23 |
| exercise | HubSpot builder exercises (GitHub) | https://github.com/hubspotdev/builder-exercises/tree/main | the hands-on exercises the videos follow (Hannah's "One job, three tools: following up on stalled deals") | opened 2026-11-24 |
| dev-signup | Create a free HubSpot developer account | https://app.hubspot.com/signup-hubspot/developers | standing CTA | opened 2026-11-23 |
| dev-platform-basics | Developer platform basics | https://developers.hubspot.com/developer-platform-basics | getting started on the developer platform | opened 2026-11-23 |
| account-types | HubSpot account types (developer test accounts) | https://developers.hubspot.com/docs/getting-started/account-types | where to try things safely | linked 2026-11-23 |
| changelog | HubSpot developer changelog | https://developers.hubspot.com/changelog | what's new | opened 2026-11-23 |
| community | HubSpot builder and developer community | https://developers.hubspot.com/community | standing CTA | linked 2026-11-23 |
| dev-slack | HubSpot developer Slack | https://developers.hubspot.com/slack | community, peers | linked 2026-11-23 |
| subscribe | Subscribe to HubSpot Developers | https://www.youtube.com/@HubSpotDevelopers?sub_confirmation=1 | every video (no UTM) | linked 2026-11-23 |

For finding more docs pages (not for descriptions): the docs index, https://developers.hubspot.com/docs/llms.txt.
