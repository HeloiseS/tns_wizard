# My TNS Wizard

Helper to report spectroscopic classifications to TNS without having to manually fill a form. 

This is mostly aimed at myself and my direct collaborators.



###  If you're not Simon de Wet of Heloise Stevance
(or someone from the ATLAS SAAO project team). Don't use this directly. I've hard coded the Classifiers' names, the remarks citing the observatories and bots involved and all the logic of the dialogue is built around classifications by SALT or Lesedi (Mookodi).

If you stumbled upong this repo looking for an example, instead directly download the [TNS example code](https://www.wis-tns.org/sites/default/files/api/tns2_sample_codes/bulk_report.zip) (it's a little hidden in their [API docs](https://www.wis-tns.org/content/tns-getting-started#API-bulk))

### How does it work?

It's a single interactive CLI script: it asks you for the classification details, uploads the
spectrum file(s), and submits the bulk classification report via the TNS API.

It has a template JSON report and fills in the gaps with your answers to the script and what is in your `tns_config_MINE.yaml`

## Installation

### 1. Clone the repo
```bash
git clone git@github.com:HeloiseS/tns_wizard.git
```
### 2. Install it
```bash
pip install -r requirements.txt
```


### 3. Configuration

Copy the template and fill in your bot's credentials:

```bash
cp tns_config_template.yaml tns_config_MINE.yaml
```

`tns_config_MINE.yaml` is gitignored — it holds your TNS API key and is never committed. **DO NOT FORCE COMMIT OR I WILL BE MAD**. 

| Field | Description |
|---|---|
| `tns_bot_id` | Your TNS bot's ID |
| `tns_bot_name` | Your TNS bot's name |
| `tns_api_key` | Your TNS bot's API key |
| `tns_host` | **Bare hostname** — `sandbox.wis-tns.org` or `www.wis-tns.org`. Do **not** include `https://`, the script prepends it itself (see Gotchas below). |
| `tns_group_id` | TNS group ID to report under — `111` for the LVRA/sandbox bot, `18` for the ATLAS group on the live server |

By default the script looks for `tns_config_MINE.yaml` next to the script. You can point it
elsewhere with `--config <path>` when calling the script (see below)

## Usage

```bash
python tns_upload_classification.py
```

Optionally point at a specific config file:

```bash
python tns_upload_classification.py --config /path/to/config.yaml
```

The script then walks you through a dialogue:

1. **Object name** — e.g. `2023zkd`
2. **Telescope/Instrument** — `Mookodi` (default) or `SALT`; sets the correct instrument ID
   and a default remark for that instrument
3. **Spectral type** — search term (e.g. `SN Ia`); pick the matching `objtypeid` from the list
4. **Observation date** — UT, `YYYY-MM-DD` or `YYYY-MM-DD HH:MM:SS` (defaults to today)
5. **Redshift** (optional)
6. **Exposure time** (optional)
7. **Reducer** (defaults to `S. de Wet`)
8. **Observer(s)** (defaults to the usual SAAO team)
9. **Additional remarks** (optional)
10. **Spectrum files**: path to the ASCII spectrum file (mandatory), and optionally a FITS
    file and a related plot/image file

> File paths cannot use wildcards or `~` — give the full, literal path.

Once the dialogue is complete, the script:

1. Uploads the spectrum file(s) to TNS
2. Writes the completed classification report to `reports/` (gitignored, regenerable)
3. Submits the bulk classification report
4. Polls TNS for a reply and prints the feedback

## Testing

```bash
pip install -r requirements-dev.txt
pytest
```

Tests run automatically on every push to `main` and on every pull request via GitHub Actions.

## Known "gotcha": `tns_host` must be a bare hostname

The script builds the API URL as `f"https://{config['tns_host']}/api"` — it prepends the
scheme itself. If `tns_host` is set to a full URL (e.g. `https://www.wis-tns.org`) instead of
a bare domain, `requests` will fail with a `NameResolutionError` for `host='https'`.

## Repo layout

- `tns_upload_classification.py` — the whole tool (dialogue, upload, submit, poll for reply)
- `tns_codes.json` — TNS lookup tables (object types, instrument ids, etc.)
- `tns_classification_report_template.json` — skeleton for the bulk classification report
- `tests/` — unit tests (pytest)
- `reports/` — generated classification reports, one per run (gitignored)
