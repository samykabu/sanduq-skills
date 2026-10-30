# Starting the roles as subagents

Every phase starts its workers in parallel, one subagent each, with the same brief shape. The skill
needs no agent definition files: each harness's built-in general subagent takes the brief.

## By harness

| Harness | How to start a worker | Notes |
| --- | --- | --- |
| Claude Code | The Agent tool with the general-purpose agent; several calls in one message run in parallel | Background agents notify you when they finish; do not poll their output |
| Codex | Ask for subagents explicitly ("spawn one subagent per brief below, in parallel"); the `default` or `worker` agent takes the brief | Codex only starts subagents when told to. Subagents inherit the sandbox and approvals |
| OpenCode | The Task tool with the built-in `general` subagent, one call per brief | A subagent uses the calling agent's model unless configured otherwise. Reading outside the project asks for `external_directory` permission, which `opencode run` (non-interactive) rejects, and the subagent fails; keep workers inside the project, or allow `external_directory` in the OpenCode config |
| None of these | Run the briefs one after another in this session, rereading the inputs from disk for each | Weaker isolation; say so in the hand-off |

If the project defines its own agents for these roles (for example `.claude/agents/security.md`,
`.codex/agents/security.toml` or `.opencode/agents/security.md`), you may use them instead; the brief
stays the same.

To put critics on a different model or harness from the authors, the `delegate-task` skill can run a
brief on another agent CLI when it is installed.

## The brief

Fill every field. Paths are absolute.

```text
You are the <role(s)> on a planning majlis for <project>. Read your role brief first:
<SKILL_DIR>/references/personas/<role>.md (one file per role in your group).

Objective: <one sentence: what this file must achieve>.
Inputs, read in full: <paths>.
Output: write exactly one file, <path>, following <SKILL_DIR>/references/templates/<template>.md.
Boundaries: write no other file; do not edit the inputs; read only inside the project folder (a
fact outside it, such as a library's source, goes in the UNVERIFIED list); <critics: you wrote none
of the inputs and have not seen their authors' reasoning>.
Rules: never invent a number (cite a source, state the method, or mark it UNVERIFIED); cite recon
facts as F-n and record items as DR-n, SP-n, OD-n.
Return: the output path and at most five lines: outcome, scores if any, blockers if any.
```

## After a phase

Read each returned summary, then the files themselves where the next phase depends on them. A worker
that returned no file, or a file that breaks its template, is re-run with the defect named; never
patch over it by writing the content yourself.

A worker that fails (a denied permission, a timeout) is re-run once with the cause named in its
brief, for example "stay inside the project folder". If it fails again, run only that worker in
this session and note it in the hand-off. One failed worker never switches the whole run to
sequential mode.
