# Roster: which roles sit

The set of roles is fixed. Five are core and always sit; four are optional and are chosen per run.

## Core roles (always seated)

| Role | Domain | Why it always sits |
| --- | --- | --- |
| `chair` | Investment, scope, unit economics, IP | Owns the gate and whether the plan is worth building |
| `product` | Users, problem, positioning, packaging | Owns what is built and for whom |
| `architect` | Structure, data, boundaries, build | Owns how it fits together |
| `security` | Threats, trust boundaries, abuse, compliance | Every system has an attacker |
| `qa-chaos` | Testability, failure modes, chaos, acceptance | Every plan needs a way to prove it works |

## Optional roles

Propose a role when the request matches its signals. Propose it as **recommended**, **possible** or
**not needed**, with one reason each.

| Role | Domain | Signals that recommend it |
| --- | --- | --- |
| `ux` | Screens, flows, copy, accessibility, RTL | A UI, a phone app, a website, onboarding, forms, a design system |
| `integrations` | Third-party platforms, AI models and agents, APIs, SDK internals | Calls an external API or SaaS, uses an LLM or agent, a plugin or extension of another product, webhooks |
| `devops-finops` | CI/CD, hosting, runners, releases, running cost | Hosted service, deployments, infrastructure, cloud cost, release pipeline, on-call |
| `end-user` | The lazy, distracted real user | Anyone other than the builders will use it: setup, first run, daily use |

A purely internal library with no UI usually needs none; a hosted consumer app usually needs all four.

## Asking the user

Ask once, before recon, in this shape:

```text
Core roles (always): chair, product, architect, security, qa-chaos.
Optional roles, my proposal from your request:
- ux: recommended. It has a web dashboard and a phone screen.
- integrations: recommended. It calls the GitHub API and an LLM.
- devops-finops: possible. It is self-hosted; say yes if you want hosting cost planned.
- end-user: recommended. Non-developers set it up.
Which optional roles should sit?
```

With a question tool that supports multiple choice, offer the optional roles as a multi-select with
the recommended ones listed first. Record the answer in `00-brief.md` under **Roster**.

## Critic groups

Critics work in groups of seated roles. Use these groups and drop roles that are not seated; a group
with no seated role disappears, and a lone optional role joins the nearest group.

| Group | Roles | Attacks |
| --- | --- | --- |
| `security-chaos` | security, qa-chaos | Threats, abuse, failure, recovery, test gaps |
| `commercial` | chair, product, devops-finops | Value, scope, cost, pricing, delivery risk |
| `architecture` | architect, integrations | Structure, data, platform facts, build |
| `experience` | ux, end-user | Flows, copy, setup, the 5-minute journey |

Every critic is a fresh subagent that wrote no track and saw no author's reasoning. A role may lead a
track and later critique as a new instance; the critic instance still never wrote what it reviews.
