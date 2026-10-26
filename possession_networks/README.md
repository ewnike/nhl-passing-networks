# possnet: possession and passing networks

Capstone project for the University of Michigan MADS program (SIADS). The research question is whether network measures of a team's passing and possession structure (degree, betweenness, PageRank, HITS, clustering) add predictive information beyond traditional shot based metrics such as Corsi.

Free, public, pass level NHL data is hard (functionally impossible) to find. The plan is therefore to build and validate the complete pipeline on StatsBomb open soccer event data, then port it to hockey through an adapter once suitable hockey data is either found or generated.

## Status

| Step | Description | State |
|---|---|---|
| 1 | Repository, environment, structure | done |
| 2 | Pull and cache StatsBomb open data, record license | done |
| 3 | Canonical event schema (data contract) | done |
| 4 | Validation and exploration | done |
| 5 | Directed weighted pass networks and centralities | done |
| 6 | Possession sequences labeled by outcome (two schemes) | done |
| 7 | Zone grid Markov chain and pass value (four configurations) | done |
| 8 | Incremental value test with grouped cross validation | done |
| 9 | Optional: motifs, temporal networks, embeddings | planned |
| 10 | Hockey adapter | in progress: 10a data pull done, 10b adapter next |
| 11 | Interactive web app | in progress |

## Quick start

```bash
git clone <this repository>
cd possession_networks

# Option A: conda
conda env create -f environment.yml && conda activate possnet
# Option B: pip (Python 3.11 or newer)
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && pip install -e .

python scripts/01_pull_data.py
python scripts/02_build_canonical.py
python scripts/03_validate.py
python scripts/04_explore.py
python scripts/05_build_networks.py
python scripts/06_build_possessions.py
python scripts/07_example_network_figure.py
python scripts/08_markov_xt.py
python scripts/09_incremental_value.py
python scripts/10_incremental_figures.py
python scripts/11_build_app_data.py
```

Hockey (step 10a, Stathletes Big Data Cup 2026, separate config and outputs):

```bash
python scripts/01b_pull_stathletes.py            # events and shifts for all 10 games, prints an inventory
python scripts/01b_pull_stathletes.py --summary  # inventory of what is already cached
```

Use `python scripts/01_pull_data.py --max-matches 10` for a quick test and `--list` to see every available competition season. The default is Premier League 2015/2016 (380 matches, 20 teams). Change `config/project.yaml` to analyze a different season.

## Repository layout

```
config/sample.yaml           synthetic sample configuration
config/project.yaml          competition, season, pinned data commit, directories
config/hockey.yaml           Stathletes Big Data Cup release, hockey directories
data/raw/                    cached licensed JSON (git ignored, never committed)
data/interim/                canonical Parquet tables (git ignored)
data/processed/              derived features (git ignored)
data/manifests/              SHA 256 manifest of every cached file (committed, no data)
docs/data_contract.md        generated schema documentation
docs/decisions.md            decision log and open questions
docs/ATTRIBUTION.md          code and data attribution
src/possnet/sources/         downloaders and caches (one module per provider)
src/possnet/adapters/        provider to canonical mapping (one module per provider)
src/possnet/schema/          the data contract, dtype coercion, doc generator
src/possnet/validate/        contract and semantic checks
src/possnet/explore/         exploratory summaries
src/possnet/network/         pass network construction, centralities, season aggregation
src/possnet/possession/      possession sequences and outcome labels
src/possnet/markov/          zone grid, absorbing chain, expected threat values, stability
src/possnet/incremental/     step 8: model table, fold safe xT, grouped CV, bootstrap, sensitivity grid
src/possnet/viz/             pitch drawing and figure helpers
scripts/                     numbered entry points, run in order
tests/                       unit tests (synthetic data only, no licensed data)
outputs/                     tables and figures
app/                         local explorer (step 11), open app/index.html after `python scripts/11_build_app_data.py`
```

All paths are relative to the repository root and are resolved from `src/possnet/paths.py`, so the project runs from any clone location.

## Pipeline design

Provider specific code lives only in `sources/` and `adapters/`. Every adapter produces three tables (`matches`, `events`, `appearances`) defined in `src/possnet/schema/contract.py` and documented in `docs/data_contract.md`. Network, possession, Markov, and modeling code reads only canonical tables, which is what makes a later hockey port a matter of writing one adapter.

Key conventions in the contract:

* Coordinates are meters from the acting team's attacking frame: origin at the center of the surface, +x toward the goal being attacked, +y to the acting team's left.
* `minutes_played` is real elapsed minutes on the surface (time on ice for hockey), the denominator for per minute normalization.
* `possession_id` and `play_pattern` allow set pieces and restarts to be separated from open play.

## Network and possession results (Premier League 2015/2016)

* Networks: 760 team matches, open play and all pass scopes. Per player: in and out strength, partner counts, betweenness, PageRank, HITS hub and authority, weighted clustering, with per 90 versions of the volume measures. Per team: density, reciprocity, concentration (Gini) of strength and PageRank, PageRank entropy, top three PageRank share, clustering, algebraic connectivity.
* Sequences: 111,725 sequences (147 per team match). Goals per team match 1.35 and shots 13.0, matching the season totals exactly. Two outcome schemes are stored side by side (`outcome_strict`, `outcome_broad`) and `starts_dead_ball` allows set piece starts to be included or excluded. See `docs/decisions.md` D8 to D11.

## Markov chain and pass value results (Premier League 2015/2016)

* A 12 by 8 zone grid with absorbing states goal, shot, and turnover. Paths follow where each ball action starts and are cut at the first shot. Censored endings add no terminal transition.
* Four configurations run side by side: strict or broad turnover, crossed with open play only or all sequences. Zone values agree almost perfectly (Spearman above 0.99). Player per 90 goal threat agrees at 0.96 to 0.99 across configurations.
* Split half reliability of player per 90 threat (293 players with at least 450 minutes per half): 0.65 to 0.84 depending on configuration.
* Player value of a successful pass or carry is the gain in zone value; a failed pass is charged the zone value it lost. Dead ball restarts are excluded. Outputs: `outputs/tables/xt_player_season.csv`, `markov_zone_values.csv`, `markov_stability.csv`, `markov_config_comparison.csv`, and `outputs/figures/markov_zone_value.png`.

## Local explorer

`python scripts/11_build_app_data.py` writes `app/data.js` (git ignored, your machine only). Open `app/index.html` in a browser. Networks has two views of any match. Live play follows the ball along every logged pass, carry and shot, with the pass line growing as the ball moves and an optional layer of opposing players. Network fixes players at their average positions and sends a pulse along each link, so every line is a sum of passes you watched. Time runs pass by pass or in real time, with step buttons (comma and period keys). Player positions between events are estimates, because the open data has no tracking. Zones and Evidence show the Markov chain and the step 8 results.

## Reproducibility

The configuration pins the upstream data to a specific commit, and every downloaded file is hashed in `data/manifests/`. Two people running the pull get byte identical data, and a changed file is detectable. Random seeds will be set in `config/project.yaml` when modeling starts.

## Data access and license

See `DATA_ACCESS.md`. In short: StatsBomb open data may be used for research and analysis, may not be redistributed or commercially exploited, and any published analysis must credit StatsBomb and show its logo. Raw data is therefore not in this repository. Each team member runs the pull script on their own machine.

## Validation summary (Premier League 2015/2016)

380 matches, 1,313,773 events, 368,619 passes, 644 players, 71,884 possessions. Of 37 checks, all 35 error severity checks pass and 2 informational checks flag known source behavior (see `docs/decisions.md`). Full results are written to `outputs/tables/validation_report.csv`.

## Attribution

Data: StatsBomb open data. Replace the text credit on figures with the StatsBomb logo from their media pack (save as `docs/assets/statsbomb_logo.png`; the file is intentionally not bundled). Code attribution policy is in `docs/ATTRIBUTION.md`.
