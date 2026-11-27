# ACME SOC detections: how we work

Detections for Splunk Enterprise Security, kept as code. Read this before changing anything.

## Source of truth

- Community rules live in `sigma/rules/`, synced from [SigmaHQ](https://github.com/SigmaHQ/sigma) under the
  Detection Rule License 1.1 (`sigma/LICENSE.Detection.Rules.md`). Never edit them; keep their authors.
- A detection in `detections/<domain>/` is a contentctl YAML built from one Sigma rule and reuses that rule's `id`.
  Copy the shape of an existing detection. Name its file after the detection's `name` in lowercase words joined by
  underscores (`Process Memory Dump Via Comsvcs DLL` is `process_memory_dump_via_comsvcs_dll.yml`); that stem also
  names its test file, its filter macro, and the macro file.

## Writing a detection

1. Convert: `sigma convert -t splunk -p splunk_cim -f data_model <rule.yml>`. Keep the `where` clause exactly as
   sigma-cli prints it; CI checks that it still matches the Sigma rule.
2. Wrap it in our template (see `detections/endpoint/*.yml`): `security_content_summariesonly`, the standard `by`
   fields, `drop_dm_object_name(Processes)`, the two `security_content_ctime` macros, and `<file_stem>_filter` last.
3. Metadata from the Sigma rule: `mitre_attack_id` from its `attack.t*` tags, `known_false_positives` from
   `falsepositives`. Sigma `level` high or critical is `type: TTP` with risk score 64 (high) or 80 (critical);
   medium is `type: Anomaly`, risk score 40. T1003 techniques go in the `Credential Dumping` story.
   `status: production`, `enabled_by_default: true`.
4. Tests: `tests/<file_stem>.yml` with at least one `match` case from real attack data and one `none` case
   (harmless activity that looks similar). Event files go in `tests/data/`, one Sysmon XML event per line. A case
   built by editing a real event says "crafted" in its name. Name an existing ESCU rule in `compare_with` when there
   is one.
5. `contentctl build` must pass before you push.

## Tuning

Only in `macros/<file_stem>_filter.yml`, as narrow as possible (an account and a host together, never a whole
process name), with a description saying who approved it and why. Add the tuned activity as a `none` test case.

## Shipping

- Never write to Splunk directly. Splunk access from a workstation is read-only.
- Branch, commit, open a pull request to `main`. The `validate` workflow builds the app, replays every test into the
  `dac_ci` index, compares with ESCU, checks a week of endpoint data for noise, and has Splunk AI Toolkit triage any
  hits. It must be green.
- A person reviews and merges. The `deploy` workflow then installs the detections in Enterprise Security.
