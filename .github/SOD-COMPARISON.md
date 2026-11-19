# Research behind the SOD signup comparison

Research notes from November 19, 2026. The alternate signup comparison is saved in commit `e7c2f4a`.

## How the companies show what their products do

- **Blitzy** invites buyers to inspect public builds that resemble their own projects. Its cash-ledger example includes a COBOL-to-Java change, tests and a migration runbook. A buyer can read the actual changes and judge how much work they would accept. [Blitzy public samples](https://github.com/blitzy-public-samples) · [Cash-ledger pull request](https://github.com/blitzy-public-samples/blitzy-stock-trader/pull/2)
- **Opsera** compares development approaches by asking where people approve decisions. Forge links a requirement, its tests and the person approving a change. That gives a team with sign-off obligations something specific to evaluate. [Opsera’s comparison](https://opsera.ai/blog/software-factory-vs-dark-factory) · [Forge](https://opsera.ai/forge)
- **8090** follows a requirement across roles. A work order carries the blueprint, acceptance criteria and links to implementation. Its setup guide also documents self-service checkout per seat, with extra usage billed separately. The old “Talk to us” entry missed that route. [Work orders](https://docs.8090.ai/modules/work-orders) · [Setup and checkout](https://docs.8090.ai/general/quickstart)
- **Cognition** describes different jobs for Devin and its Data Analyst. An engineer can review a bug fix as a pull request. An analyst can ask about a connected database and inspect the SQL or a chart. The Data Analyst guide excludes free and trial plans. [Devin overview](https://docs.devin.ai/get-started/devin-intro) · [Data Analyst](https://docs.devin.ai/work-with-devin/data-analyst)
- **Factory** recommends comparing agents on a familiar task with a clear acceptance decision. Its own Missions guide shows what a reviewer can inspect as a larger project progresses, down to a feature’s commits and validation criteria. [Factory’s comparison guide](https://factory.com/articles/best-coding-agent-for-your-team) · [Mission Control](https://docs.factory.com/missions/running-app)

## Rationale for the alternate comparison

Each product gets the same two questions and a source the buyer can open. For Sneferu, readers can see a private-VM build in the walkthrough and inspect the findings and underlying evidence in a published scientific investigation. [Build walkthrough](../sod/signup-new/index.html#see) · [Published Research Expedition](https://sneferu.ai/research/rex-c8661466/)

The old price row put a VM subscription, an annual enterprise tier and invitations to contact sales in the same column of answers. A cost comparison would need a defined workload, team size, hosting arrangement and usage assumptions. The signup page already gives the monthly VM fee and a worked usage example. [Sneferu billing example](../sod/signup-new/index.html#usageExample) · [8090 checkout](https://docs.8090.ai/general/quickstart) · [Opsera pricing](https://opsera.ai/pricing)
