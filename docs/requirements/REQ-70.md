# REQ-70 — Status/info as reconstructed UI metadata

https://github.com/matthewhand/open-swarm/issues/789

Parent [#407](https://github.com/matthewhand/open-swarm/issues/407) was closed by the landed [#765](https://github.com/matthewhand/open-swarm/pull/765) filter belt. Reconstruction Success is [#789](https://github.com/matthewhand/open-swarm/issues/789).

Status/info/hop/PR-opened/prior-history chrome is written to the `ui_events` side channel (`append_event`). CLI session select and PR-opened persist do not `messages.append({role: status})`. The #765 `messages_for_model` / `is_ui_only_role` helpers remain a belt. The UI reconstructs display from `turns` + `ui_events`.
