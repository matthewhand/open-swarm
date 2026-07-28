let meta = #{
    name: "moa-team-megafan",
    description: "Massive parallel audit of MoA team path: review, verify, test, fix",
    phases: [
        #{ title: "Audit", detail: "64+ parallel reviewers across code/docs/tests/security" },
        #{ title: "Verify", detail: "adversarial skeptics on every finding" },
        #{ title: "Hardening", detail: "tests, edge cases, and concrete fixes" },
        #{ title: "Synthesize", detail: "single report of confirmed work" },
    ],
    when_to_use: "After MoA team/consensus commits; max fan-out verification and hardening",
};

let findings_schema = #{
    "type": "object",
    "required": ["findings", "scope_ok"],
    "properties": #{
        "scope_ok": #{ "type": "boolean" },
        "findings": #{
            "type": "array",
            "maxItems": 6,
            "items": #{
                "type": "object",
                "required": ["severity", "file", "issue", "evidence"],
                "properties": #{
                    "severity": #{ "type": "string" },
                    "file": #{ "type": "string" },
                    "issue": #{ "type": "string" },
                    "evidence": #{ "type": "string" },
                    "fix_hint": #{ "type": "string" },
                },
            },
        },
        "notes": #{ "type": "string" },
    },
};

let verdict_schema = #{
    "type": "object",
    "required": ["real", "reason", "evidence"],
    "properties": #{
        "real": #{ "type": "boolean" },
        "reason": #{ "type": "string" },
        "evidence": #{ "type": "string" },
        "severity": #{ "type": "string" },
    },
};

let fix_schema = #{
    "type": "object",
    "required": ["applied", "summary", "files_touched"],
    "properties": #{
        "applied": #{ "type": "boolean" },
        "summary": #{ "type": "string" },
        "files_touched": #{ "type": "array", "items": #{ "type": "string" } },
        "tests_run": #{ "type": "string" },
    },
};

let test_schema = #{
    "type": "object",
    "required": ["passed", "summary", "failures"],
    "properties": #{
        "passed": #{ "type": "boolean" },
        "summary": #{ "type": "string" },
        "failures": #{ "type": "array", "items": #{ "type": "string" } },
    },
};

// Fixed 64-slot audit matrix — each agent has a concrete, non-overlapping brief.
let audits = [
    #{ id: "a01", focus: "team.py API surface correctness (TeamTask, MoATeamResult, parse_team_tasks)", path: "src/swarm/core/moa/team.py" },
    #{ id: "a02", focus: "team.py specialist implementer path and default output paths", path: "src/swarm/core/moa/team.py" },
    #{ id: "a03", focus: "team.py tester and docs specialists content safety and path traversal", path: "src/swarm/core/moa/team.py" },
    #{ id: "a04", focus: "team.py researcher specialist and list_files/read_file usage", path: "src/swarm/core/moa/team.py" },
    #{ id: "a05", focus: "team.py run_moa_consensus never writes and panel_wrote invariant", path: "src/swarm/core/moa/team.py" },
    #{ id: "a06", focus: "team.py run_moa_then_team seed_files and write tracking clearing", path: "src/swarm/core/moa/team.py" },
    #{ id: "a07", focus: "team.py logging completeness (champagne moa.team / moa.collect linkage)", path: "src/swarm/core/moa/team.py" },
    #{ id: "a08", focus: "team.py parse_team_tasks edge cases empty, nested lists, unknown purposes", path: "src/swarm/core/moa/team.py" },
    #{ id: "a09", focus: "team.py format_team_text and team_result_to_payload serialization", path: "src/swarm/core/moa/team.py" },
    #{ id: "a10", focus: "agents_orchestrator.py delegation to run_moa_then_team correctness", path: "src/swarm/core/moa/agents_orchestrator.py" },
    #{ id: "a11", focus: "agents_orchestrator.py build_moa_orchestrator_agents circular import risk", path: "src/swarm/core/moa/agents_orchestrator.py" },
    #{ id: "a12", focus: "agents_orchestrator.py SpecialistTask alias and SPECIALIST_PURPOSES re-export", path: "src/swarm/core/moa/agents_orchestrator.py" },
    #{ id: "a13", focus: "agents_orchestrator.py MoAAgentsOrchestratorResult.as_persona_result", path: "src/swarm/core/moa/agents_orchestrator.py" },
    #{ id: "a14", focus: "orchestrator.py champagne log coverage without behavior change", path: "src/swarm/core/moa/orchestrator.py" },
    #{ id: "a15", focus: "orchestrator.py collect_opinions timeout path still returns ParticipantOpinion", path: "src/swarm/core/moa/orchestrator.py" },
    #{ id: "a16", focus: "orchestrator.py determine primary logging when analysis missing", path: "src/swarm/core/moa/orchestrator.py" },
    #{ id: "a17", focus: "cli.py leaf imports avoid package circular import with tools/team", path: "src/swarm/core/moa/cli.py" },
    #{ id: "a18", focus: "tools.py consult_moa always act=False and backend validation", path: "src/swarm/core/moa/tools.py" },
    #{ id: "a19", focus: "moa __init__.py public exports completeness vs team API", path: "src/swarm/core/moa/__init__.py" },
    #{ id: "a20", focus: "swarm_cli.py moa --team and --act mutual exclusion", path: "src/swarm/core/swarm_cli.py" },
    #{ id: "a21", focus: "swarm_cli.py --team requires --workdir validation", path: "src/swarm/core/swarm_cli.py" },
    #{ id: "a22", focus: "swarm_cli.py --team-tasks default and parse wiring", path: "src/swarm/core/swarm_cli.py" },
    #{ id: "a23", focus: "swarm_cli.py verbose logging force=True side effects", path: "src/swarm/core/swarm_cli.py" },
    #{ id: "a24", focus: "swarm_cli.py json vs text output for team mode", path: "src/swarm/core/swarm_cli.py" },
    #{ id: "a25", focus: "swarm_cli.py trace path write for team mode", path: "src/swarm/core/swarm_cli.py" },
    #{ id: "a26", focus: "blueprint_moa_orchestrator parse_team_tasks delegation", path: "src/swarm/blueprints/moa_orchestrator/blueprint_moa_orchestrator.py" },
    #{ id: "a27", focus: "paths.py _safe_mkdir best-effort semantics and remaining risks", path: "src/swarm/core/paths.py" },
    #{ id: "a28", focus: "WorkspaceTools path sandboxing for specialist writes", path: "src/swarm/core/persona_swarm.py" },
    #{ id: "a29", focus: "test_moa_team.py coverage gaps vs team.py branches", path: "tests/core/test_moa_team.py" },
    #{ id: "a30", focus: "test_moa_command.py XDG isolation and team CLI assertions", path: "tests/cli/test_moa_command.py" },
    #{ id: "a31", focus: "test_moa_agents_orchestrator.py still valid after refactor", path: "tests/core/test_moa_agents_orchestrator.py" },
    #{ id: "a32", focus: "test_paths.py broken cache symlink case completeness", path: "tests/core/test_paths.py" },
    #{ id: "a33", focus: "docs/MOA.md team CLI examples accuracy", path: "docs/MOA.md" },
    #{ id: "a34", focus: "docs/SWARM_WORKFLOWS.md MoA vs persona vs team consistency", path: "docs/SWARM_WORKFLOWS.md" },
    #{ id: "a35", focus: "docs/SKILLS_AND_CONSENSUS_WALKTHROUGH.md links to new team path", path: "docs/SKILLS_AND_CONSENSUS_WALKTHROUGH.md" },
    #{ id: "a36", focus: "example moa-consensus-vs-team README vs actual API", path: "docs/examples/moa-consensus-vs-team/README.md" },
    #{ id: "a37", focus: "example moa-orchestrator README vs agents_orchestrator", path: "docs/examples/moa-orchestrator/README.md" },
    #{ id: "a38", focus: "demo_moa_consensus_vs_team.py correctness and invariants", path: "scripts/demo_moa_consensus_vs_team.py" },
    #{ id: "a39", focus: "trace_moa_champagne.py log assertions and CI-safety", path: "scripts/trace_moa_champagne.py" },
    #{ id: "a40", focus: "CHANGELOG Unreleased claims match shipped code", path: "CHANGELOG.md" },
    #{ id: "a41", focus: "security: specialist cannot write outside workspace root", path: "src/swarm/core/moa/team.py" },
    #{ id: "a42", focus: "security: fake backend default responses do not leak secrets", path: "src/swarm/core/moa/team.py" },
    #{ id: "a43", focus: "security: team mode cannot enable act write side channel", path: "src/swarm/core/swarm_cli.py" },
    #{ id: "a44", focus: "concurrency: concurrent specialist tasks not parallelized — intentional?", path: "src/swarm/core/moa/team.py" },
    #{ id: "a45", focus: "error handling: unknown specialist purpose returns ok=False", path: "src/swarm/core/moa/team.py" },
    #{ id: "a46", focus: "error handling: consult_moa failures propagate in team path", path: "src/swarm/core/moa/team.py" },
    #{ id: "a47", focus: "typing: TeamTask fields optional output_path and list typing", path: "src/swarm/core/moa/team.py" },
    #{ id: "a48", focus: "compat: SpecialistTask identity with TeamTask for blueprints", path: "src/swarm/core/moa/agents_orchestrator.py" },
    #{ id: "a49", focus: "import graph: team -> tools -> cli -> not package __init__", path: "src/swarm/core/moa/" },
    #{ id: "a50", focus: "import graph: package __init__ importing team and agents_orchestrator", path: "src/swarm/core/moa/__init__.py" },
    #{ id: "a51", focus: "missing tests: parse_team_tasks list-of-dicts and TeamTask items", path: "tests/core/test_moa_team.py" },
    #{ id: "a52", focus: "missing tests: unknown purpose specialist", path: "tests/core/test_moa_team.py" },
    #{ id: "a53", focus: "missing tests: consensus_only via CLI without --team", path: "tests/cli/test_moa_command.py" },
    #{ id: "a54", focus: "missing tests: verbose -v without team still works", path: "tests/cli/test_moa_command.py" },
    #{ id: "a55", focus: "example capture scripts shell safety and PYTHONPATH", path: "docs/examples/moa-consensus-vs-team/scripts/capture_example_runs.sh" },
    #{ id: "a56", focus: "example orchestrator capture scripts shell safety", path: "docs/examples/moa-orchestrator/scripts/capture_example_runs.sh" },
    #{ id: "a57", focus: "diagram mmd sources match README mental model", path: "docs/examples/moa-consensus-vs-team/assets/" },
    #{ id: "a58", focus: "FEATURE_STATUS or README mention of team path if expected", path: "FEATURE_STATUS.md" },
    #{ id: "a59", focus: "backends FakeParticipantBackend interaction with team defaults", path: "src/swarm/core/moa/backends.py" },
    #{ id: "a60", focus: "policy WriteDeniedError path still works with team mode", path: "src/swarm/core/moa/policy.py" },
    #{ id: "a61", focus: "schema parse_proposal still used for determination quality", path: "src/swarm/core/moa/schema.py" },
    #{ id: "a62", focus: "race: asyncio.run nested from CLI team path", path: "src/swarm/core/swarm_cli.py" },
    #{ id: "a63", focus: "docs examples assets JSON shape matches team_result_to_payload", path: "docs/examples/moa-consensus-vs-team/assets/05-demo-contrast.json" },
    #{ id: "a64", focus: "overall product claim: no openai-agents dependency on pure team path", path: "src/swarm/core/moa/team.py" },
];

phase("Audit");
log("Launching " + audits.len().to_string() + " parallel audit agents");

let audit_jobs = [];
for a in audits {
    let p = "";
    p += "You are a meticulous code auditor on the open-swarm repo at /home/matthewh/open-swarm. ";
    p += "Focus ONLY on: " + a.focus + ". Primary path: " + a.path + ". ";
    p += "Use read_file/grep/list_dir on the real code — never invent from memory. ";
    p += "Also check related tests if relevant. ";
    p += "Report at most 6 concrete findings with severity (critical|high|medium|low|nit), file, issue, evidence (quote lines or test names), and optional fix_hint. ";
    p += "Empty findings is valid ONLY after you actually inspected the code. Set scope_ok=true if your focus area is sound. ";
    p += "Do NOT fix anything. Read-only. Commit under review is feafbb5e (MoA pure team path).";
    audit_jobs.push(#{
        prompt: p,
        label: a.id,
        capability_mode: "read-only",
        agent_type: "explore",
        output_schema: findings_schema,
    });
}
let audit_results = parallel(audit_jobs);

let all_findings = [];
let audit_ok = 0;
let audit_fail = 0;
for r in audit_results {
    if r == () || !r.success {
        audit_fail += 1;
    } else {
        audit_ok += 1;
        if r.output.findings != () {
            for f in r.output.findings {
                all_findings.push(f);
            }
        }
    }
}
log("Audit complete: ok=" + audit_ok.to_string() + " fail=" + audit_fail.to_string() + " raw_findings=" + all_findings.len().to_string());

// Cap verification fan-out: prioritize critical/high first, then rest, max 80.
let prioritized = [];
for f in all_findings {
    if f.severity == "critical" || f.severity == "high" {
        prioritized.push(f);
    }
}
for f in all_findings {
    if f.severity != "critical" && f.severity != "high" {
        prioritized.push(f);
    }
}
let to_verify = [];
let i = 0;
while i < prioritized.len() && i < 80 {
    to_verify.push(prioritized[i]);
    i += 1;
}
if prioritized.len() > 80 {
    log("Truncated verification to 80 of " + prioritized.len().to_string() + " findings");
}

if to_verify.len() == 0 {
    phase("Hardening");
    // Still run test panels even with zero findings.
    let tjobs = [];
    let t1 = "";
    t1 += "In /home/matthewh/open-swarm run: PYTHONPATH=src python -m pytest ";
    t1 += "tests/core/test_moa_team.py tests/cli/test_moa_command.py ";
    t1 += "tests/core/test_moa_agents_orchestrator.py tests/core/test_moa.py ";
    t1 += "tests/core/test_paths.py -q --tb=short --no-cov. ";
    t1 += "Return passed, summary, failures list.";
    tjobs.push(#{ prompt: t1, label: "test-core-moa", capability_mode: "execute", output_schema: test_schema });
    let t2 = "";
    t2 += "In /home/matthewh/open-swarm run: PYTHONPATH=src python scripts/demo_moa_consensus_vs_team.py 2>&1 | tail -40. ";
    t2 += "Confirm invariants_ok. Return passed, summary, failures.";
    tjobs.push(#{ prompt: t2, label: "test-demo", capability_mode: "execute", output_schema: test_schema });
    let t3 = "";
    t3 += "In /home/matthewh/open-swarm run: PYTHONPATH=src python scripts/trace_moa_champagne.py 2>&1 | tail -30. ";
    t3 += "Return passed, summary, failures.";
    tjobs.push(#{ prompt: t3, label: "test-trace", capability_mode: "execute", output_schema: test_schema });
    let tres = parallel(tjobs);
    phase("Synthesize");
    let report = "# MoA megafan report\n\nNo audit findings. Tests: " + json_encode(tres) + "\n";
    let sp = write_scratch_file("moa-megafan-report.md", report);
    complete(#{ summary: "No findings; tests ran", path: sp, findings: 0 });
}

phase("Verify");
log("Verifying " + to_verify.len().to_string() + " findings with independent skeptics");
let vjobs = [];
for f in to_verify {
    let vp = "";
    vp += "Adversarially verify this finding in /home/matthewh/open-swarm by reading the shipped code yourself. ";
    vp += "Claim severity=" + f.severity + " file=" + f.file + " issue=" + f.issue + " claimed_evidence=" + f.evidence + ". ";
    vp += "Set real=true ONLY with concrete independent evidence (quotes, line numbers, failing logic). ";
    vp += "Default real=false if uncertain, outdated, or nit-level style only. ";
    vp += "Use read_file/grep. Read-only.";
    vjobs.push(#{
        prompt: vp,
        label: "v-" + f.severity,
        capability_mode: "read-only",
        agent_type: "explore",
        output_schema: verdict_schema,
    });
}
let verdicts = parallel(vjobs);

let confirmed = [];
let vi = 0;
for v in verdicts {
    if v != () && v.success && v.output.real == true && v.output.evidence != () && v.output.evidence != "" {
        let item = to_verify[vi];
        confirmed.push(#{
            severity: item.severity,
            file: item.file,
            issue: item.issue,
            evidence: v.output.evidence,
            reason: v.output.reason,
            fix_hint: item.fix_hint,
        });
    }
    vi += 1;
}
log("Confirmed after skepticism: " + confirmed.len().to_string() + "/" + to_verify.len().to_string());

phase("Hardening");
// Always run test + edge-case generator panels.
let hard_jobs = [];
let h1 = "";
h1 += "In /home/matthewh/open-swarm run with shell: ";
h1 += "PYTHONPATH=src python -m pytest tests/core/test_moa_team.py tests/cli/test_moa_command.py ";
h1 += "tests/core/test_moa_agents_orchestrator.py tests/core/test_moa.py tests/core/test_paths.py ";
h1 += "tests/core/test_moa_leftovers.py -q --tb=short --no-cov. Report passed/summary/failures.";
hard_jobs.push(#{ prompt: h1, label: "pytest-moa", capability_mode: "execute", output_schema: test_schema });

let h2 = "";
h2 += "In /home/matthewh/open-swarm: PYTHONPATH=src python scripts/demo_moa_consensus_vs_team.py ; ";
h2 += "PYTHONPATH=src python scripts/trace_moa_champagne.py. Report combined passed/summary/failures.";
hard_jobs.push(#{ prompt: h2, label: "demos", capability_mode: "execute", output_schema: test_schema });

let h3 = "";
h3 += "In /home/matthewh/open-swarm inspect import graph: PYTHONPATH=src python -c \"from swarm.core.moa import *; from swarm.core.swarm_cli import app; print('ok')\". ";
h3 += "Also try nested asyncio concerns. Report passed/summary/failures.";
hard_jobs.push(#{ prompt: h3, label: "imports", capability_mode: "execute", output_schema: test_schema });

// Up to 16 fix agents for top confirmed issues (worktree-isolated; parent merges later if needed).
let fix_count = 0;
for c in confirmed {
    if fix_count < 16 {
        let sev = c.severity;
        if sev == "critical" || sev == "high" || sev == "medium" {
            let fp = "";
            fp += "Fix this confirmed issue in /home/matthewh/open-swarm. ";
            fp += "Issue: " + c.issue + " in " + c.file + ". Evidence: " + c.evidence + ". ";
            if c.fix_hint != () { fp += "Hint: " + c.fix_hint + ". "; }
            fp += "Make a minimal correct fix. Add/adjust a unit test if practical. ";
            fp += "Run the relevant pytest. Do NOT commit. Do NOT push. ";
            fp += "Return applied, summary, files_touched, tests_run.";
            hard_jobs.push(#{
                prompt: fp,
                label: "fix-" + fix_count.to_string(),
                capability_mode: "all",
                isolation_worktree: true,
                output_schema: fix_schema,
            });
            fix_count += 1;
        }
    }
}

// Coverage fill agents (always): missing tests / edge cases
let cov_prompts = [
    "Add tests in tests/core/test_moa_team.py for parse_team_tasks list-of-dicts and TeamTask objects if missing. Run pytest on that file. Minimal change. Do not commit.",
    "Add test for unknown specialist purpose (ok=False) in tests/core/test_moa_team.py if missing. Run pytest. Do not commit.",
    "Add CLI test that -v works without --team if missing in tests/cli/test_moa_command.py. Isolate XDG. Do not commit.",
    "If FEATURE_STATUS.md or README should mention moa --team and doesn't, add a short accurate note. Minimal. Do not commit.",
];
let ci = 0;
for cp in cov_prompts {
    hard_jobs.push(#{
        prompt: "In /home/matthewh/open-swarm: " + cp,
        label: "cov-" + ci.to_string(),
        capability_mode: "all",
        isolation_worktree: true,
        output_schema: fix_schema,
    });
    ci += 1;
}

log("Hardening panel size=" + hard_jobs.len().to_string());
let hard_results = parallel(hard_jobs);

phase("Synthesize");
let applied_fixes = [];
let test_summaries = [];
for r in hard_results {
    if r != () && r.success && r.output != () {
        if r.output.applied != () {
            applied_fixes.push(r.output);
        }
        if r.output.passed != () {
            test_summaries.push(r.output);
        }
    }
}

let report = "# MoA team megafan report\n\n";
report += "## Audit\n";
report += "- agents ok: " + audit_ok.to_string() + "\n";
report += "- agents fail: " + audit_fail.to_string() + "\n";
report += "- raw findings: " + all_findings.len().to_string() + "\n";
report += "- verified: " + to_verify.len().to_string() + "\n";
report += "- confirmed: " + confirmed.len().to_string() + "\n\n";
report += "## Confirmed findings\n";
report += json_encode(confirmed);
report += "\n\n## Test summaries\n";
report += json_encode(test_summaries);
report += "\n\n## Fix attempts (worktree-isolated; may need merge)\n";
report += json_encode(applied_fixes);
report += "\n";

let spath = write_scratch_file("moa-megafan-report.md", report);
complete(#{
    summary: "confirmed=" + confirmed.len().to_string() + " fixes_attempted=" + applied_fixes.len().to_string(),
    path: spath,
    confirmed_count: confirmed.len(),
    audit_ok: audit_ok,
    audit_fail: audit_fail,
    raw_findings: all_findings.len(),
});
