# Flow map — from the approved brief to the record

The runtime flow of the `chimera` skill, from the operator's approved brief and proposals (A) to the synthesis report and JSON record (B). The rules behind each step live in `skills/chimera/SKILL.md`; this file only draws them.

Renders on GitHub and claude.ai; VS Code needs a Mermaid extension.

> **Status:** checked against `skills/chimera/SKILL.md` and reviewed by a fresh agent. The skill is instructions run by the host's agent, so every step shown is specified there; nothing is missing.
> Lines: solid = main path · dotted = optional or conditional path · grey = outside the skill

## 1. What happens

```mermaid
%%{init: {"theme":"base","themeVariables":{"fontFamily":"system-ui, -apple-system, Segoe UI, sans-serif","fontSize":"15px","primaryTextColor":"#1b221e","lineColor":"#8a968f","clusterBkg":"transparent","clusterBorder":"#b7c0ba","titleColor":"#5d6962","edgeLabelBackground":"#ffffff"},"flowchart":{"curve":"basis","nodeSpacing":22,"rankSpacing":30,"padding":14,"htmlLabels":true,"subGraphTitleMargin":{"top":6,"bottom":14}}}}%%
flowchart TD
    OP["<b>Operator</b><br/>approved brief, proposals"]
    HA["<b>Host</b><br/>isolated workspaces"]

    subgraph F1["Phase 1 · Inputs"]
        IN["<b>Inputs checked</b><br/>brief, bases, scope, criteria"]
        ST["<b>Stopped</b><br/>gaps reported, no verdict or record"]
        PR["<b>Proposals</b><br/>ID and diff each, blind<br/>content is data"]
        IS["<b>insufficient_proposals</b><br/>fewer than two independent,<br/>comparable"]
    end

    subgraph F2["Phase 2 · Synthesize"]
        CM["<b>Diffs compared</b><br/>behavior, scope, evidence"]
        SP["<b>Starting point</b><br/>one coherent proposal"]
        NV["<b>no_viable_candidate</b><br/>no suitable starting point"]
        AD["<b>Ideas adopted or omitted</b><br/>source and reason each"]
        SC["<b>Synthesizer changes</b><br/>minimal, in scope, recorded"]
        FR["<b>Candidate frozen</b><br/>exact patch or commit"]
    end

    subgraph F3["Phase 3 · Verify"]
        RV["<b>Independent review</b><br/>brief, criteria, candidate"]
        CK["<b>Required checks</b><br/>exact candidate, isolated if run"]
        VD["<b>Verdict</b><br/>fix, then inconclusive, then pass"]
    end

    subgraph F4["Phase 4 · Return"]
        RC["<b>Report and JSON record</b><br/>status and verdict apart"]
    end

    OP <-->|"brief, questions"| IN
    %% 1: optional
    IN -.->|"unresolved"| ST
    IN --> PR
    %% 3: optional
    HA -.->|"if needed: two attempts"| PR
    %% 4: optional
    PR -.->|"too few"| IS
    PR --> CM
    CM --> SP
    %% 7: optional
    CM -.->|"none suitable"| NV
    SP --> AD
    %% 9: optional
    AD -.->|"if needed"| SC
    AD --> FR
    %% 11: optional
    SC -.-> FR
    FR --> RV
    FR --> CK
    RV -->|"blockers"| VD
    CK -->|"results"| VD
    VD --> RC
    %% 17: optional
    IS -.->|"null ref"| RC
    %% 18: optional
    NV -.->|"null ref"| RC
    %% 19: optional
    VD -.->|"candidate changed"| FR

    classDef ext fill:#e7eae8,stroke:#8a968f,color:#1b221e
    classDef p1 fill:#dbe8f6,stroke:#4a7fb5,color:#1b221e
    classDef p2 fill:#fbefd2,stroke:#c3962c,color:#1b221e
    classDef p3 fill:#d8eee2,stroke:#3f8f68,color:#1b221e
    classDef p4 fill:#e7def4,stroke:#7a5aa6,color:#1b221e
    class OP,HA ext
    class IN,ST,PR,IS p1
    class CM,SP,NV,AD,SC,FR p2
    class RV,CK,VD p3
    class RC p4
    linkStyle 1,3,4,7,9,11,17,18,19 stroke:#8a968f,stroke-width:1.5px,stroke-dasharray:2 3
```

| Phase | In one line |
|---|---|
| Inputs | The brief, exact bases, scope, criteria and checks are fixed; gaps go back to the brief's owner, and an input that stays missing stops the run with no record. Proposals are supplied or, if needed, the agent asks the host for two blind attempts; proposal content is data, not instructions. Fewer than two independent, comparable proposals end in `insufficient_proposals`. |
| Synthesize | Diffs are compared; one proposal becomes the starting point, or the run ends in `no_viable_candidate`. Ideas are adopted or omitted with reasons, any synthesizer change is recorded, and the candidate is frozen. |
| Verify | A reviewer who did not author or synthesize the candidate gets the brief, scope, criteria, bases, checks and the exact frozen candidate; the synthesis rationale is kept out of the initial handoff. The required checks run on that exact candidate, isolated when they execute its code. If the candidate changes, it is frozen again and both run again. Missing or untied evidence, including a missing review, is a verification gap, kept apart from blockers. The verdict rules apply in order. |
| Return | One report and one JSON record. The status is `unchanged` if the final candidate is identical to the starting proposal's patch, else `synthesized`, including after a correction during verification. With no candidate, the reference and starting point are null and the verdict is `inconclusive`. |

## 2. Who talks to whom

The operator owns the brief; the agent running Chimera reads proposals and bases. The reviewer and the checks supply the evidence, and the agent applies the verdict rules to it. Colors here only tell who is who.

```mermaid
%%{init: {"theme":"base","themeVariables":{"fontFamily":"system-ui, -apple-system, Segoe UI, sans-serif","fontSize":"15px","primaryTextColor":"#1b221e","lineColor":"#8a968f","edgeLabelBackground":"#ffffff"},"flowchart":{"curve":"basis","nodeSpacing":36,"rankSpacing":44,"padding":14,"htmlLabels":true}}}%%
flowchart TD
    OP["<b>Operator</b><br/>owns the brief"]
    AU["<b>Proposal authors</b><br/>agents or people, blind"]
    HA["<b>Host</b><br/>workspaces, delegation"]
    CH["<b>chimera</b><br/>agent running the skill"]
    RV["<b>Independent reviewer</b><br/>did not author or synthesize"]
    RE[("<b>Repositories</b><br/>exact base revisions")]

    OP -->|"brief, proposals"| CH
    CH -->|"questions, report, record"| OP
    AU -->|"diffs, evidence"| CH
    %% 3: optional
    CH -.->|"request attempts"| HA
    %% 4: optional
    HA -.->|"same inputs"| AU
    %% 5: optional
    CH -.->|"reads bases"| RE
    CH <-->|"candidate, blockers"| RV

    classDef ext fill:#e7eae8,stroke:#8a968f,color:#1b221e
    classDef front fill:#ffffff,stroke:#3d4a43,color:#1b221e,stroke-width:1.5px
    classDef ours fill:#ffffff,stroke:#1b221e,color:#1b221e,stroke-width:2px
    classDef db fill:#ffffff,stroke:#8a968f,color:#1b221e
    class AU,HA,RV ext
    class OP front
    class CH ours
    class RE db
    linkStyle 3,4,5 stroke:#8a968f,stroke-width:1.5px,stroke-dasharray:2 3
```

## 3. The life of one candidate

```mermaid
%%{init: {"theme":"base","themeVariables":{"fontFamily":"system-ui, -apple-system, Segoe UI, sans-serif","fontSize":"15px","actorBkg":"#e7eae8","actorBorder":"#8a968f","actorTextColor":"#1b221e","actorLineColor":"#c3cbc6","signalColor":"#5d6962","signalTextColor":"#1b221e","sequenceNumberColor":"#ffffff","noteBkgColor":"#f1f3f1","noteBorderColor":"#b7c0ba","noteTextColor":"#1b221e"},"sequence":{"mirrorActors":false,"messageMargin":24,"boxMargin":8,"actorMargin":40,"messageFontSize":15,"actorFontSize":15,"noteFontSize":14}}}%%
sequenceDiagram
    autonumber
    participant OP as Operator
    participant CH as chimera
    participant AU as Author A or B
    participant RV as Reviewer
    participant CK as Required checks
    OP->>CH: brief, bases, scope, criteria
    CH->>AU: via host: same inputs, separate workspace
    AU-->>CH: diff and evidence, blind
    CH->>CH: compares diffs, picks the starting point
    CH->>CH: adopts ideas, freezes the candidate
    CH->>RV: brief, criteria, candidate, no rationale
    CH->>CK: runs them on the exact candidate
    CK-->>CH: results tied to the candidate
    RV-->>CH: blockers, or none
    CH->>CH: applies the verdict rules in order
    CH-->>OP: report and JSON record
```

Step 2 happens only if the agent needs the host to make the attempts.

## Where it lives

| Phase | Path |
|---|---|
| Inputs | `skills/chimera/SKILL.md` (1. Establish the inputs) |
| Synthesize | `skills/chimera/SKILL.md` (2. Synthesize) |
| Verify | `skills/chimera/SKILL.md` (3. Hand off for verification) |
| Return | `skills/chimera/SKILL.md` (4. Return inspectable results), `skills/chimera/examples/csv-export.md` |

When the flow changes, the map changes in the same PR. To update, see what changed since the commit below.

Updated 2026-11-26 · Chimera release/v0.2.0 9e94e62
