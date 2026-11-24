# Video catalog

One entry per video: what it covers, where it lives, what it links to. Written by `yt youtube`
(youtube-meta.py build) between each video's markers; `yt published NAME URL` fills in the link and date.

<!-- video:agents-2 -->
### Connect Claude to HubSpot: Manage Deals Without Opening HubSpot

- **Slug:** `agents-2` · **Channel:** HubSpot Developers · **Series:** HubSpot Is Going Headless
- **Status:** drafted, not published
- **YouTube:** (not published yet)
- **Published:** -
- **Length:** 04:26
- **Summary:** Connects Claude to HubSpot with the HubSpot connector and has an agent create three example deals, find the stale ones and add follow-up tasks, then schedules the stale-deal check as a daily Claude task. Uses an exercise by Hannah, a HubSpot builder advocate.
- **Audience:** HubSpot admins, RevOps and builders who already use Claude and want agents to do routine CRM work
- **Topics:** HubSpot connector for Claude, HubSpot MCP server, connector scopes, deals, stale deals, tasks, scheduled tasks in Claude, headless HubSpot
- **Questions it answers:** How do I connect Claude to HubSpot? · Which scopes should the HubSpot connector get? · Can Claude create deals in HubSpot? · How do I find stale deals in HubSpot with an AI agent? · Can I schedule a recurring HubSpot task in Claude?
- **Chapters:** 00:00 HubSpot is going headless: agents in Claude · 00:26 Connect Claude to HubSpot with the connector · 01:00 Choose the connector's scopes · 01:30 Create HubSpot deals from a Claude prompt · 02:21 Find stale deals and add follow-up tasks · 03:19 Schedule the stale-deal check in Claude · 04:00 Next: the HubSpot Agent CLI
- **Links used:** [Create a free HubSpot developer account](https://app.hubspot.com/signup-hubspot/developers), [Get the HubSpot connector for Claude](https://www.hubspot.com/claude/connector), [How the HubSpot MCP server works (docs)](https://developers.hubspot.com/docs/build-with-ai/remote-mcp-server), [HubSpot Agent CLI guide](https://developers.hubspot.com/docs/developer-tooling/local-development/agent-cli/guide), [Join the HubSpot builder and developer community](https://developers.hubspot.com/community), [Subscribe to HubSpot Developers](https://www.youtube.com/@HubSpotDevelopers?sub_confirmation=1)
- **Related:** the-agent-cli (next, not published yet)
<!-- /video:agents-2 -->

<!-- video:agentcli -->
### HubSpot Agent CLI: Find Stale Deals and Create Tasks With a Saved Script

- **Slug:** `agentcli` · **Channel:** HubSpot Developers · **Series:** HubSpot Is Going Headless
- **Status:** drafted, not published
- **YouTube:** (not published yet)
- **Published:** -
- **Length:** 06:25
- **Summary:** Shows why repeat agent runs burn credits, then sets up the HubSpot Agent CLI: clone Hannah's exercise, install the CLI, log in, install skills and create a service key. An agent then finds stale deals, shows a dry run, creates follow-up tasks and saves the work as a script, which is changed to 7 days and rerun without the agent.
- **Audience:** HubSpot admins, RevOps and builders who already use AI agents and want repeatable CRM tasks without paying for an agent round trip every run
- **Topics:** HubSpot Agent CLI, service key, scopes, stale deals, follow-up tasks, dry run, saved scripts, headless HubSpot
- **Questions it answers:** How do I install the HubSpot Agent CLI and log in? · How do I create a HubSpot service key and choose its scopes? · How do I find stale deals in HubSpot with an AI agent and the CLI? · Can an agent create HubSpot follow-up tasks with a dry run first? · How do I save an agent's work as a script I can rerun without the agent?
- **Chapters:** 00:00 Why use the HubSpot Agent CLI instead of repeat agent runs · 00:30 Clone the HubSpot Agent CLI exercise in VS Code · 01:01 Install the HubSpot Agent CLI and restart the shell · 01:31 Log in to HubSpot from the CLI and approve scopes · 02:32 Install agent skills for the HubSpot Agent CLI · 03:02 Create a HubSpot service key with deals, contacts and owners scopes · 03:48 Seed example deals in HubSpot with the exercise script · 04:18 Find stale deals and create follow-up tasks with a dry run · 05:20 Check the new HubSpot tasks and the saved script · 05:35 Change the stale-deal window from 14 to 7 days · 05:50 Rerun the saved script without the agent
- **Links used:** [Create a free HubSpot developer account](https://app.hubspot.com/signup-hubspot/developers), [HubSpot Agent CLI guide](https://developers.hubspot.com/docs/developer-tooling/local-development/agent-cli/guide), [HubSpot Agent CLI public beta announcement](https://developers.hubspot.com/changelog/hubspot-agent-cli-available-in-public-beta), [Join the HubSpot builder and developer community](https://developers.hubspot.com/community), [Subscribe to HubSpot Developers](https://www.youtube.com/@HubSpotDevelopers?sub_confirmation=1)
- **Related:** agents-2 (the previous video: stale deals with Claude)
<!-- /video:agentcli -->
