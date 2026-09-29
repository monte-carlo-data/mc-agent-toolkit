---
description: Connect a warehouse to Monte Carlo — choose the deployment, reference credentials, create the warehouse and connection (REST API v2 tools)
---

Activate the Monte Carlo Onboarding skill. Discover the account and its existing deployments, agents, data stores, warehouses and connections first, show the customer that inventory and what can be added (supported integrations and credential options per deployment), then ask what they want to connect unless the input below already says. One run can onboard several integrations; check each one's support before asking anything else about it. Ask only for missing requirements about connection origin, credential custody and sample storage, then reuse or provision the appropriate deployment. Distinguish cloud-native and Generic collection agents and their network paths. Guide the connection through available v2 tools and local handoffs, writing every step the user runs locally for mc-cli (https://github.com/monte-carlo-data/mc-cli) unless they ask for Terraform or an SDK script. Keep secrets out of chat and tool calls, and tell the user why (no MCP tool accepts or returns a credential), reconcile existing credentials/warehouse/connection before creation, validate the connection and read its result, then end with created/reused IDs, the validation result and pending steps.

**User provided input**: $ARGUMENTS
