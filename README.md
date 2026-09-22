# AdVerify AgentBeats Leaderboard

AdVerify evaluates an anomaly-detection participant against 20 public
advertising campaign records. The green judge compares each reported anomaly's
type and field with its annotations and reports per-campaign precision, recall,
and F1 plus macro averages.

This fork stages the independently verified One Jump deterministic participant.
Its release workflow produced exact anomaly sets for all 20 records and then
repeated a live 20-campaign A2A assessment with each of two fresh container
pairs: 40/40 live evaluations at precision, recall, and F1 of 1.0. See
[release run 35691573711](https://github.com/onejumpinc/adverify-deterministic-agent/actions/runs/35691573711).

## Submission workflow

The workflow is deliberately manual-only and currently inert.
`ADVERIFY_AGENT_ID` remains a non-UUID placeholder in the workflow,
`scenario.toml`, and `scenario.ci.toml`. After the immutable manifest is
registered on AgentBeats, replace all three occurrences with the resulting
lowercase UUIDv7 and dispatch the workflow once from `main`.

The registration must use this immutable manifest URL:

`https://raw.githubusercontent.com/onejumpinc/adverify-deterministic-agent/727737a20d153f1f6707e5a5867b3853c6b97311/amber-manifest.json5`

Before a submission branch can be created, the workflow verifies:

- the fork, branch, run attempt, exact scenario, green registration, purple
  registration owner/category/repository/manifest, and manifest checksum;
- immutable green, participant, and AgentBeats client image digests, including
  the participant image ID that passed the release gates;
- a closed three-service Compose topology with no secrets, registry login,
  build context, host ports, override file, or unpinned runtime image;
- exactly 20 ordered campaign results, the full expected 21-true-positive
  vector, zero false positives and false negatives, and per-campaign plus macro
  precision/recall/F1 of exactly 1.0;
- the green judge's 20 ordered calls and complete immutable image and GitHub
  Actions provenance.

Evaluation runs with read-only repository permission. A separate write-scoped
job re-verifies the downloaded evidence and can add exactly three files to one
deterministically named branch based on the audited upstream commit. It neither
opens nor merges a pull request.

No model or registry secret is required. The upstream scenario included an
Anthropic key, but the pinned green judge's AdVerify path is deterministic and
the exact release validation ran without that key.

## Pinned runtime

- Green judge:
  `ghcr.io/iker592/adverify-judge@sha256:71de5628bae8088872254a72aeb358f0a4694944d41107b4ff89ed53ede002c5`
- Participant:
  `ghcr.io/onejumpinc/adverify-deterministic-agent@sha256:4e4b9eb857fe1c3afa643e1001eb46f93b16283da15461bf2014050cea3013ea`
- AgentBeats client:
  `ghcr.io/agentbeats/agentbeats-client@sha256:13dfe3ef4e583a80e7ce2fe3becd0ce3b879841368a7f4fa40b6ebbabeeb014e`

The workflow stays undispatched until the participant has a real AgentBeats
registration UUID.
