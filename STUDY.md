# Can an AI agent operate an ERP? A hands on study against SAP's public APIs

July 2026. All numbers below trace to raw run logs in `runs/` in this repository.

## Why this study exists

SAP announced the "Autonomous Enterprise" in May 2026, with more than 200 specialized agents planned across its product line. The pitch is that AI agents will operate enterprise software. This study asks a simpler, earlier question. Given today's public SAP APIs and a free, small AI model, how far does an agent actually get on ordinary business tasks?

The setup is deliberately modest, one agent loop, a free model (GPT-4o mini via GitHub Models), and SAP's public sandbox APIs for S/4HANA Cloud. Modest is the point. Whatever friction shows up here is friction every agent project will meet on day one.

## Method

The agent receives a business instruction in plain language, four tools (list services, read from an API, write to an API, finish), and at most 15 turns. It is told nothing about SAP's data model. Every model response and every API call is logged in full to a JSONL file, and the findings report is generated from those logs by a script, not written from memory. Five tasks cover the ordinary shapes of ERP work, find a master data record, filter transactional documents, create a document, summarize documents, and cross reference two objects.

## Results

Four of five tasks succeeded. The write task could not succeed, and the reason matters.

| Task | Outcome | Turns | API calls |
|---|---|---|---|
| Find a supplier and report its account group | success | 13 | 11 |
| List purchase orders for a supplier and report currencies | success | 3 | 1 |
| Create a purchase order | blocked by platform | 4 | 2 |
| Summarize supplier invoices | success | 6 | 4 |
| Report a product's base unit and type | success | 6 | 4 |

## Finding 1. Reading the enterprise works, with stumbling

The agent completed every read task. But the simplest sounding task, find one supplier by name, took 11 API calls because the agent had to discover SAP's data model by trial and error. It guessed entity names that do not exist (A_PaymentTerms, A_SupplierRole), used a filter function the OData v2 gateway rejects, and recovered each time by reading the error and adjusting. The stumbles are not model stupidity, they are the cost of a fifty year old data model exposed through an API that assumes the caller already knows it.

## Finding 2. Writing to the enterprise is walled off

The purchase order creation attempt received HTTP 405, with SAP's message stating the public sandbox supports GET operations only and write operations must be tested against a customer's own system. So the public evaluation surface of the world's largest ERP vendor lets an agent look but not act. Anyone claiming their agent "works with SAP" on the basis of public APIs is describing a read only integration, a distinction buyers should press on.

## Finding 3. Verbosity is a tax on agents

SAP's raw responses are large enough that a single unfiltered API reply overflowed the free model's 8,000 token request limit and killed the first run outright (the failed log is preserved in `runs/`). The fix was aggressive trimming of responses before the model sees them. Enterprise APIs were designed for programs that extract one field and move on. Agents read everything, so response weight becomes a real cost and a real failure mode.

## Finding 4. Error messages are the agent's documentation

The agent never saw SAP documentation, only error responses. When those errors were specific ("Property contains not found in type A_BusinessPartnerType") the agent corrected course in one turn. Vague errors produced repeated failing guesses. For API owners preparing for agent traffic, error message quality is no longer a developer nicety, it is the interface.

## Does a smarter model fix it? Three brains, same wall

After the first run set, we repeated all five tasks with a frontier model (GPT-4.1) and a strong open source model (Llama 4 Maverick), same harness, same tools, same logging.

| Task | GPT-4o mini (small) | GPT-4.1 (frontier) | Llama 4 Maverick (open) |
|---|---|---|---|
| Find a supplier | success, 11 API calls | success, 1 API call | gave up after 3 calls |
| List purchase orders | success | success | success |
| Create a purchase order | blocked, 405 | blocked, 405 | blocked, 405 |
| Summarize invoices | success | success | success |
| Product base unit and type | success | success | success |

Two lessons fall out of the comparison.

First, model quality buys efficiency, not new capability. GPT-4.1 found the supplier in a single call where the small model needed eleven, because it knew to query A_Supplier with the right filter on the first try. Llama 4 gave up on the same task. Better models pay less discovery tax, but the tax exists for all of them.

Second, the wall does not care how smart you are. All three models hit the same 405 refusal on the write task. No amount of model intelligence changes a platform policy, which is exactly the point buyers should take away. Capability claims about agents operating enterprise systems are bounded by what the platform permits, not by how good the model is.

## What this means

1. For anyone planning agent projects on SAP, budget for the discovery problem. Agents will need curated tool definitions or metadata access, not raw OData endpoints and optimism.
2. For buyers, ask vendors whether their SAP agent integration reads, writes, or both, and where the write path was actually tested.
3. For platform owners, the levers that decide agent success are unglamorous, lean responses, precise errors, and discoverable metadata.

## Limits of this study

One small free model, five tasks, one run set, and a sandbox with demo data. The success rate is an existence proof, not a benchmark. The write finding reflects SAP's public sandbox policy, not the capability of a licensed S/4HANA system. Nothing here measures Joule or SAP's own agents, which run inside the wall with advantages this experiment's agent lacked.

## Reproduce it

Everything needed is in this repository, see README.md. Total cost to reproduce, zero. The model tier is free, the SAP sandbox key is free, and the runner executes locally or in GitHub Actions.
