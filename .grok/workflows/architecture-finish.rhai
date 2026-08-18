// Architecture finish fan-out — three senior themes from ADR-001 / AUTH / glossary.
// Prefer running via durable 15m scheduler; this script is for ad-hoc megafan.

let meta = #{
  name: "architecture-finish",
  description: "Fan out agents on dual-UI, auth coherence, and product vocabulary cut",
};

fn theme_prompt(theme, detail) {
  "Architecture finish for open-swarm at /home/matthewh/open-swarm.\n"
    + "Locked: Django primary UI; SPA Chat only (docs/ADR-001-primary-ui.md).\n"
    + "Theme: " + theme + "\n"
    + detail + "\n"
    + "Ship one concrete commit+push. No questions. Do not remount SPA Builder.\n"
}

let results = parallel([
  agent(#{
    role: "general-purpose",
    prompt: theme_prompt("Dual UI", "Quarantine leftover SPA pages; App routes only / and /chat; fix tests/docs."),
    description: "UI consolidation",
  }),
  agent(#{
    role: "general-purpose",
    prompt: theme_prompt("Auth trust", "Tighten docs/AUTH.md links; reduce one auth special-case if safe."),
    description: "Auth coherence",
  }),
  agent(#{
    role: "general-purpose",
    prompt: theme_prompt("Product cut", "Glossary honesty; remove dead CLI/extension cruft safely."),
    description: "Vocabulary cut",
  }),
]);

print("architecture-finish panel done");
