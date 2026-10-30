# Data access statement

Verified on 2026 10 06 from the public sources linked below. Re verify before final submission, because terms and hosting can change without notice.

## Primary data: StatsBomb open data (soccer)

| Item | Detail |
|---|---|
| Provider | StatsBomb (now part of Hudl) |
| Location | https://github.com/hudl/open-data (the agreement text still names github.com/statsbomb/open-data, which redirects) |
| Pinned commit | `4b73468fc5b0f1950f9f66fada70ad3a4f9327cb` (master head on 2026 10 06) |
| Competition season used | Premier League 2015/2016 (competition_id 2, season_id 27), 380 matches |
| Format | JSON files: competitions, matches, events, lineups (360 data is available for some matches and is not used) |
| Agreement | https://github.com/hudl/open-data/blob/master/LICENSE.pdf ("StatsBomb Public Data User Agreement") |
| Registration | The agreement asks every user to register name and email at https://statsbomb.com/resource-centre/ |
| Logo | https://statsbomb.com/media-pack/ |

### Terms that shape this project (summary of the agreement; read the original)

* Purpose: analysis, research, and shared understanding of the data. It is described as a research tool.
* Not allowed: editing, distorting, distributing, reproducing, selling, or otherwise providing the data to any external or third party; commercially exploiting the data or analysis derived from it; illegal or defamatory use; reverse engineering the service.
* Required: any publication of analysis formed from the data must be accredited with the StatsBomb brand logo. The repository README adds that the data source must be stated as StatsBomb.
* Ownership: the data remains StatsBomb's property. StatsBomb may withhold or suspend the service at any time without notice.
* The data is provided as is, with no warranty of accuracy or completeness.

### How the project complies

1. Raw data and the canonical tables derived from it are git ignored and never committed. `.gitignore` enforces this and `data/manifests/` contains only file names, sizes, and hashes.
2. Each team member registers with StatsBomb and runs `scripts/01_pull_data.py` on their own machine. Do not pass the cached files to teammates, instructors, or cloud storage. Share the repository, not the data.
3. Anything published (README figures, report, web app) credits StatsBomb and shows the StatsBomb logo.
4. Published outputs are analysis results: aggregated metrics, network features, model results, and plots. They do not reproduce event level or match level source records. Row level derived tables (per possession, per team match) are git ignored for the same reason. The web app in step 11 will serve precomputed aggregates and will not serve source events.
5. The work is for academic coursework only. No commercial use. The author's employer plays no role in this project and receives none of its data or code.
6. A reliability caveat is carried into the report: StatsBomb gives no accuracy warranty, and checks in this repository found source quirks (see `docs/decisions.md`).

### Local explorer (2026 10 07)

`app/data.js` is built on the author's machine for personal use and is git ignored. It must not be shared or published. If the app is ever published, return to the aggregate only plan below.

### Author decision (2026 10 06)

Showing precomputed season and player aggregates in the web app is acceptable to the project author, who will confirm the terms before publishing. This is not a legal clearance.

### Open compliance question

Whether precomputed per match network metrics shown in a public web app count as "analysis" or as reproducing the data is not answered by the agreement text. Plan: show season and player level aggregates and per match values only in aggregate plots, and confirm with the course instructor (and StatsBomb support if the app will be public) before publishing anything at match level.

## Hockey data: Stathletes Big Data Cup 2026 (step 10, in use)

Verified on 2026 10 26 from the public repository and its legal file.

| Item | Detail |
|---|---|
| Provider | Stathletes, for the Big Data Cup hackathon (with the Rotman School and UTSPAN) |
| Location | https://github.com/bigdatacup/Big-Data-Cup-2026, files are assets of the release tagged `Data` |
| Agreement | https://github.com/bigdatacup/Big-Data-Cup-2026/blob/main/legal.md ("Stathletes Public Data User Agreement") |
| Content | 10 games from October and November 2025, teams anonymised as Team A to Team L. Per game: events, shifts, and player and puck tracking per period from broadcast video. A camera orientation index covers all games. |
| Format | CSV. Events and shifts total about 2 MB. Tracking is about 25 MB per period per game and is off by default. |
| Registration | None found. The files are public release assets. |
| Contact | bigdatacup@stathletes.com for anything the agreement does not answer |

### Terms that shape this project (summary of the agreement; read the original)

* Purpose: the data is made public to promote research and a deeper understanding of hockey.
* Allowed: research produced from the data is free to be shared publicly, provided it is not used for profit.
* Not stated: whether the data itself may be redistributed, and whether use outside the competition is covered. The agreement is silent, so this project treats the raw files as not redistributable.
* Stathletes keeps the right to publish any work submitted for the hackathon. This only matters if we submit to the competition.
* The competition README says tracking data must be used in any competition entry. That is a submission rule. It is not a condition of the agreement and does not obviously apply to coursework, so the event network does not wait on tracking.

### How the project complies

1. Same rules as StatsBomb. Raw files and the canonical tables derived from them are git ignored (`data/raw/*`, `data/interim/*`). `data/manifests/stathletes_bdc_2026.json` holds only file names, sizes and SHA 256 hashes.
2. Each team member runs `python scripts/01b_pull_stathletes.py` on their own machine. Share the repository, not the data.
3. The work is academic coursework only, with no commercial use.
4. Hockey output is kept in `outputs/hockey/`, apart from the committed soccer results. Row level derived tables stay local, as for soccer.
5. Open question carried over from StatsBomb: the agreement allows sharing research, which plausibly covers aggregated network metrics in a public app, but not event level or game level rows. Until confirmed, a public app shows aggregates only.

### Reliability notes found while pulling

* The release tag is not a commit, so Stathletes could replace a file without notice. Every repeat pull compares hashes with the last manifest and logs any change.
* The competition README and the files disagree in places (shift columns are named differently, the tracking file has an extra jersey number column). The puller checks the real headers and stops if a column it relies on disappears. See `docs/decisions.md` D22.

## Hockey data candidates (research notes from 2026 10 06)

The Stathletes row below is superseded by the section above. All Three Zones is still not adopted.


These are research notes from public web pages on 2026 10 06. Nothing has been downloaded and no license has been read, so none of this is a compliance clearance.

| Source | What public pages say | What still needs checking |
|---|---|---|
| Stathletes Big Data Cup | Hosted by Stathletes, the Rotman School, and UTSPAN. Provides Stathletes tracked event data for a high calibre league plus player tracking generated from broadcast video. The 2026 page says tracking data must be used in competition projects. Earlier editions (2021 to 2024) released data on GitHub, including women's hockey play by play. Anyone may participate. | Whether pass events carry a recipient, the current download location and license for each edition, whether use outside the competition is allowed, redistribution limits |
| All Three Zones (Corey Sznajder) | Manually tracked NHL microstats such as zone entries and exits, collected publicly since 2016 to 17, typically 30 to 50 games per team per season. Access is through a paid subscription, with raw data via links for subscribers. An older 2013 14 dataset is sold for a small fee. | Whether it contains enough pass recipient information for networks (it appears to be zone transition focused), license and redistribution terms, whether a paywalled dataset can be used in a graded public project |

Practical implication: a paid, subscriber only dataset cannot be committed, and probably cannot back a public web app, without written permission. Data that cannot be shown publicly would limit step 11 for hockey.
