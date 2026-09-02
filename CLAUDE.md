# CLAUDE.md - Project Level Instructions - TNS Wizard

## About the project

`tns_wizard` reports spectroscopic classifications of ATLAS-discovered transients back to the
[Transient Name Server](https://www.wis-tns.org/). It's the downstream half of a pipeline that
starts in `atlas_sao`: ATLAS finds a transient, a VRA (Virtual Research Assistant) scores it,
it gets scheduled for spectroscopic follow-up on Mookodi (Lesedi telescope) or SALT, and once a
classification spectrum comes back, this tool writes the classification report up to TNS.

Currently it's one interactive CLI script (`tns_upload_classification.py`): it asks a human for
the classification details, then uploads spectrum files and submits the bulk classification report
via the TNS API.

## History and relation to other repos

This code used to live at `atlas_sao/scripts/tns/`. It was split out into its own repo on
2026-09-02 because it's a distinct concern from `atlas_sao` (which handles populating the
Mookodi/SALT follow-up *lists* — the upstream trigger side, not TNS reporting).

- **atlas_sao** (`~/software/atlas_sao`): upstream. Scores ATLAS transients, populates the
  Mookodi/SALT follow-up lists, triggers observations via `atlasapiclient` + the SAAO
  Intelligent Observatory framework.
- **atlasapiclient** (`~/software/atlasapiclient`): the ATLAS transient server API client used
  by `atlas_sao`. **Not** a dependency of this repo — `tns_wizard` only talks to the TNS API
  directly (`requests` + `pyyaml`, no other project deps).

## People

- Simon de Wet: SAAO scientist, main user of this tool (fills in the classification dialogue,
  provides the spectrum files), also the SALT/Mookodi-SAAO contact.
- Nic Erasmus: in charge of Mookodi robotisation.
- Stephen Smartt: PM, result-oriented, not a software dev.
- Ken Smith: RSE, ATLAS/PanSTARRS DB admin, Lasair core dev, H's closest technical collaborator.

## Known gotcha: `tns_host` must be a bare hostname

`tns_upload_classification.py` builds the API URL as `f"https://{config['tns_host']}/api"` —
it prepends the scheme itself. `tns_host` in the config must therefore be a **bare domain**
(`sandbox.wis-tns.org` or `www.wis-tns.org`), never a full URL with `https://` in it.

If someone puts a full URL in `tns_host` by mistake, `requests` ends up parsing a malformed
URL and you get a `NameResolutionError` with `host='https'` — that exact symptom was diagnosed
from a traceback Simon hit on 2026-09-02 (config had `https://www.wis-tns.org` where it should
have been `www.wis-tns.org`).

## Config

- `tns_config_template.yaml`: template, tracked in git.
- `tns_config_MINE.yaml`: real credentials, **gitignored**, not to ever be committed.
- Fields: `tns_bot_id`, `tns_bot_name`, `tns_api_key`, `tns_host`, `tns_group_id`.
  - `tns_group_id`: `111` for the LVRA/sandbox bot, `18` for the ATLAS group on the live server.
    Read from config into the report at submit time — not hardcoded in the report template.

## File layout

- `tns_upload_classification.py` — the whole tool (dialogue, upload, submit, poll for reply).
- `tns_codes.json` — TNS lookup tables (object types, instrument ids, etc).
- `tns_classification_report_template.json` — skeleton for the bulk classification report
  payload; fields like `groupid` are intentionally blank and filled in from config/dialogue.
- `tns_examples/` — TNS's own reference example scripts (gitignored, not our code, kept locally
  for reference only).
- `reports/` — generated classification reports, one per run (gitignored, regenerable).

## Status (as of 2026-09-02)

- Just split out of `atlas_sao`. `main` has the moved code.
- No tests yet — that's the next piece of work.
- The `tns_group_id` config field (above) was added the same day as the split.
