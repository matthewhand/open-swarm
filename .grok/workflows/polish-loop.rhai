let meta = #{
    name: "polish-loop",
    description: "15-minute polish pulse: defects, UI/UX, screenshot alignment, quality",
    phases: [
        #{ title: "Discover", detail: "parallel pedantic scanners" },
        #{ title: "Verify", detail: "adversarial check on top findings" },
        #{ title: "Apply", detail: "minimal fixes in worktrees where safe" },
        #{ title: "Report", detail: "scratch summary for the parent" },
    ],
    when_to_use: "Recurring polish during long compute windows",
};

let findings_schema = #{
    "type": "object",
    "required": ["findings", "pulse"],
    "properties": #{
        "pulse": #{ "type": "string" },
        "findings": #{
            "type": "array",
            "maxItems": 8,
            "items": #{
                "type": "object",
                "required": ["severity", "area", "issue", "evidence", "fix_hint"],
                "properties": #{
                    "severity": #{ "type": "string" },
                    "area": #{ "type": "string" },
                    "issue": #{ "type": "string" },
                    "evidence": #{ "type": "string" },
                    "fix_hint": #{ "type": "string" },
                },
            },
        },
    },
};

let verdict_schema = #{
    "type": "object",
    "required": ["real", "reason", "evidence"],
    "properties": #{
        "real": #{ "type": "boolean" },
        "reason": #{ "type": "string" },
        "evidence": #{ "type": "string" },
    },
};

let fix_schema = #{
    "type": "object",
    "required": ["applied", "summary", "files_touched"],
    "properties": #{
        "applied": #{ "type": "boolean" },
        "summary": #{ "type": "string" },
        "files_touched": #{ "type": "array", "items": #{ "type": "string" } },
    },
};

let pulse = if args == () { "manual" } else if args.pulse == () { "manual" } else { args.pulse };

let focuses = [
    "docs/GUIDED_TOUR.md screenshot captions vs actual PNG content (read images with read_file)",
    "docs/USER_JOURNEY.md screenshot captions vs PNGs; missing embeds for sessions/profiles",
    "docs/SCREENSHOTS.md registry completeness vs files on disk under docs/screenshots/",
    "USERGUIDE.md MoA --team/--workdir honesty and missing CLI examples for moa/moa-init/skills",
    "webui/frontend SPA a11y: focus rings, aria, modal focus trap regressions",
    "Django templates base nav consistency: sessions, profiles, teams active states",
    "scripts/capture_user_journey.py PAGES list vs SCREENSHOTS registry drift",
    "Broken or stale links in README/USERGUIDE/GUIDED_TOUR",
    "Ruff-fixable issues in src/swarm/core/moa and swarm_cli (pedantic quality)",
    "Mobile screenshot captions vs mobile/*.png (read images)",
    "Empty-state honesty in my-blueprints.png vs doc text",
    "Settings/progress meter text alignment with settings.png",
    "Chat spa-chat.png login gate honesty in GUIDED_TOUR",
    "Blueprint library pagination/Show more vs blueprint-library.png",
    "Test flakes or skips related to screenshots/userguide captures",
    "Dead CSS / unused SPA routes after Django-canonical redirects",
];

phase("Discover");
log("polish-loop pulse=" + pulse + " scanners=" + focuses.len().to_string());

let jobs = [];
let i = 0;
for f in focuses {
    let p = "";
    p += "You are a pedantic polish auditor for open-swarm at the repository root. ";
    p += "Pulse id: " + pulse + ". Focus ONLY on: " + f + ". ";
    p += "Use read_file/grep/list_dir (and read PNG images visually when relevant). ";
    p += "Do not invent UI that is not in the repo. Prefer concrete file:line or image evidence. ";
    p += "Return at most 8 findings with severity critical|high|medium|low|nit, area, issue, evidence, fix_hint. ";
    p += "Empty findings only after real inspection. Read-only.";
    jobs.push(#{
        prompt: p,
        label: "scan-" + i.to_string(),
        capability_mode: "read-only",
        agent_type: "explore",
        output_schema: findings_schema,
    });
    i += 1;
}
let results = parallel(jobs);

let all = [];
for r in results {
    if r != () && r.success && r.output.findings != () {
        for f in r.output.findings { all.push(f); }
    }
}
log("raw findings=" + all.len().to_string());

let prioritized = [];
for f in all {
    if f.severity == "critical" || f.severity == "high" { prioritized.push(f); }
}
for f in all {
    if f.severity == "medium" { prioritized.push(f); }
}
for f in all {
    if f.severity != "critical" && f.severity != "high" && f.severity != "medium" {
        prioritized.push(f);
    }
}

let to_verify = [];
let vi = 0;
while vi < prioritized.len() && vi < 24 {
    to_verify.push(prioritized[vi]);
    vi += 1;
}

if to_verify.len() == 0 {
    let report = "# Polish pulse " + pulse + "\n\nNo findings.\n";
    let sp = write_scratch_file("polish-pulse.md", report);
    complete(#{ summary: "no findings", path: sp, pulse: pulse, findings: 0 });
}

phase("Verify");
let vjobs = [];
for f in to_verify {
    let vp = "";
    vp += "Adversarially verify this polish finding by reading the repo yourself. ";
    vp += "severity=" + f.severity + " area=" + f.area + " issue=" + f.issue + " claimed=" + f.evidence + ". ";
    vp += "real=true only with independent evidence. Prefer false for nits/style. Read-only.";
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
let j = 0;
for v in verdicts {
    if v != () && v.success && v.output.real == true && v.output.evidence != () && v.output.evidence != "" {
        confirmed.push(to_verify[j]);
    }
    j += 1;
}
log("confirmed=" + confirmed.len().to_string());

phase("Apply");
let fjobs = [];
let fi = 0;
for c in confirmed {
    if fi < 8 {
        if c.severity == "critical" || c.severity == "high" || c.severity == "medium" {
            let fp = "";
            fp += "Apply a minimal correct polish fix in the open-swarm repo. ";
            fp += "Issue: " + c.issue + " Area: " + c.area + " Evidence: " + c.evidence + ". ";
            fp += "Hint: " + c.fix_hint + ". ";
            fp += "Do not regenerate large binaries unless capture script is the only fix. ";
            fp += "Do not commit or push. Prefer docs/caption/test/small UI fixes. ";
            fp += "Return applied, summary, files_touched.";
            fjobs.push(#{
                prompt: fp,
                label: "fix-" + fi.to_string(),
                capability_mode: "all",
                isolation_worktree: true,
                output_schema: fix_schema,
            });
            fi += 1;
        }
    }
}

let applied = [];
if fjobs.len() > 0 {
    let fres = parallel(fjobs);
    for r in fres {
        if r != () && r.success && r.output != () { applied.push(r.output); }
    }
}

phase("Report");
let report = "# Polish pulse " + pulse + "\n\n";
report += "- raw: " + all.len().to_string() + "\n";
report += "- verified: " + to_verify.len().to_string() + "\n";
report += "- confirmed: " + confirmed.len().to_string() + "\n";
report += "- fix attempts: " + applied.len().to_string() + "\n\n";
report += "## Confirmed\n" + json_encode(confirmed) + "\n\n";
report += "## Fixes\n" + json_encode(applied) + "\n";
let sp = write_scratch_file("polish-pulse.md", report);
complete(#{
    summary: "confirmed=" + confirmed.len().to_string() + " fixes=" + applied.len().to_string(),
    path: sp,
    pulse: pulse,
    confirmed_count: confirmed.len(),
});
