# NHL Passing Networks

## Overview

Hockey is fundamentally a connected system.

The puck moves between players, players create options for one another, and teams generate offense through sequences of interactions. Those interactions are not isolated events. They form structures: passing chains, breakout patterns, transition routes, possession sequences, and recurring relationships between players and areas of the rink.

Network analysis provides a natural framework for studying those structures.

Rather than evaluating hockey events independently, this project will model puck movement as a set of connected player and spatial relationships. The goal is to understand how players and teams move the puck, how those movement patterns differ across game situations, and whether network structure can provide information beyond traditional hockey metrics such as Corsi.

This project is being developed as part of the University of Michigan Master of Applied Data Science capstone.

---

## Motivation

Previous work on Corsi provides an important starting point for this project.

Corsi measures shot-attempt differential and gives us useful information about what happened while a player or group of players was on the ice. It can tell us whether a team generated or surrendered more shot attempts during a player's minutes.

What Corsi does not necessarily explain is how those outcomes were created.

A possession that eventually produces a shot attempt may include:

- a defensive-zone recovery,
- a breakout pass,
- multiple neutral-zone transitions,
- a controlled offensive-zone entry,
- several offensive-zone passes,
- a lateral pass through dangerous ice,
- and finally a shot attempt.

Traditional event summaries can capture pieces of that sequence, but they often lose the connected structure of the play.

Network analysis gives us a way to preserve and study that structure.

The central motivation of this project is therefore to connect puck movement and passing structure back to prior possession research and ask whether network characteristics can explain relationships that Corsi alone cannot identify.

---

## Research Objective

The central research question is:

> Can player and spatial network structure help explain how hockey teams create and maintain possession, and does that structure provide useful information beyond conventional possession measures such as Corsi?

The project will initially focus on association rather than causation.

Network measures will not be interpreted as causing changes in production, possession, or team performance.

Instead, the project will investigate whether network-derived measures:

1. reproduce patterns previously observed with Corsi,
2. help explain those patterns,
3. contradict them in informative ways,
4. identify relationships that Corsi alone cannot detect,
5. or provide incremental explanatory or predictive information beyond conventional hockey variables.

This distinction is important. The initial goal is not to claim that PageRank, betweenness, or another network statistic causes production. The goal is to determine whether network structure captures meaningful information about how puck possession and offensive opportunities are created.

---

## Core Idea

The project will construct two complementary network representations.

### 1. Player Passing Networks

Players are represented as nodes.

Completed passes and other puck-transfer events become directed edges between players.

Example:

```text
Player A --------> Player B
         pass
```

Edges may be weighted by:

* number of completed passes,
* number of possession transfers,
* number of successful receptions,
* frequency within a game or season,
* or context-specific interactions.

Potential network measures include:

* in-degree
* out-degree
* weighted degree
* betweenness centrality
* closeness centrality
* PageRank
* HITS hubs and authorities
* clustering
* density
* reciprocity
* motifs
* community structure

These measures may help identify players who function as:

* puck-distribution hubs,
* transition players,
* primary playmakers,
* possession intermediaries,
* breakout facilitators,
* or important connectors between linemates.

### 2. Spatial Puck-Movement Networks

Spatial regions of the rink are represented as nodes.

Passes and puck transitions between locations become directed edges.

Example:

```text
Defensive-zone corner
        |
        v
Defensive half-wall
        |
        v
Neutral-zone lane
        |
        v
Offensive half-wall
        |
        v
High slot
```
This representation allows us to study puck movement through space rather than only player-to-player relationships.

Potential applications include:

* defensive-zone breakouts,
* neutral-zone transitions,
* offensive-zone entries,
* zone exits,
* puck progression,
* spatial bottlenecks,
* high-value passing routes,
* entries into dangerous areas,
* repeated team transition structures,
* and differences between successful and unsuccessful possessions.

The spatial network is a key part of the project. Pass coordinates are not optional metadata; they are central to the research design.

### 3. Why Coordinates Matter

The minimum useful passing event for this project must include both the starting and ending location of the pass.

Without coordinates, we can build a player network.

With coordinates, we can also determine how the puck moved through the rink.

That allows us to distinguish:

* a breakout pass from a lateral defensive-zone pass,
* a neutral-zone transition from an offensive-zone cycle,
* a controlled zone entry from a failed transition,
* movement toward dangerous ice from movement away from it,
* and repeated team-specific spatial patterns.

Coordinates therefore allow us to connect player-network structure to tactical hockey behavior.

### 4. Minimum Event-Level Data Requirements
The current minimum target schema is:

```text
game_id
season
period
game_time
event_sequence

team_id
strength_state

passer_id
receiver_id

pass_start_x
pass_start_y
pass_end_x
pass_end_y

pass_complete
```

Additional useful fields may include:

```text
score_state
possession_id
pass_type
zone_entry_indicator
zone_exit_indicator
shot_assist_indicator
shot_generated_indicator
under_pressure
```
Some of these may be supplied by the data source.

Others may be derived from the event coordinates and game context.

### 5. Existing Player Database

A major asset already exists for this project.

A historical NHL player database has been developed covering approximately ten NHL seasons.

It includes:

* canonical player identifiers,
* disambiguated player identities,
* player-season history,
* team information,
* Corsi and possession metrics,
* and other player-level historical statistics.

The most recent season still needs to be added.

This database is important because it gives the project an established identity layer and a historical performance layer before any new passing data is introduced.

The goal is not to rebuild player identity resolution from scratch.

Instead, new passing-event data will be joined to the existing player database through canonical player IDs.

Conceptually:

```text
Historical Player Data
        |
        | player_id
        v
Passing Event Data
        |
        v
Player + Spatial Networks
        |
        v
Network-Derived Features
        |
        v
Corsi / Production / Team Outcomes
```
The existing historical database should remain an upstream source of truth rather than being duplicated wholesale inside this repository.

### 6. Relationship to Prior Corsi Research

One of the main goals of the capstone is to connect the network results back to prior Corsi work.

Corsi tells us something about the outcome of possession while a player is on the ice.

Network analysis may help explain how that possession was created.

For example, two players may have similar Corsi results but occupy very different roles in the underlying possession network.

One may function as a high-volume distribution hub.

Another may act as a bridge between defensive-zone possession and neutral-zone transition.

Another may contribute primarily through offensive-zone circulation or dangerous-area puck movement.

The project will investigate whether network characteristics help distinguish those roles.

Possible questions include:

* Do high-Corsi players also occupy highly central network positions?
* Do strong possession players consistently serve as passing hubs?
* Are some players important because they bridge otherwise disconnected areas of a team’s passing network?
* Do network roles persist across seasons?
* Do those roles change when players change teams or linemates?
* Do certain network structures appear before strong Corsi outcomes?
* Can network structure explain cases where Corsi and traditional production disagree?
* Are some players more valuable to puck progression than their shot-attempt results suggest?

### 7. Tactical Questions

The project may eventually examine questions such as:

* Does a team have a recognizable breakout network?
* Which defenseman acts as the principal bridge from defensive-zone possession to neutral-zone transition?
* Which forwards function as primary receiving hubs during controlled exits?
* Do successful zone entries arise from different network structures than failed entries?
* Does a power play repeatedly use the same three-player passing motif?
* Which rink regions function as hubs or authorities?
* Do certain player combinations create shorter or more direct paths to dangerous ice?
* Does network structure differ at 5v5, 5v4, and 4v5?
* Can a team’s passing network be characterized as a spatial fingerprint?
* Are those fingerprints stable across games or seasons?
* How do line combinations change network structure?
* Do network features add information beyond possession metrics such as Corsi?

### 8. Temporal Networks

Hockey networks are dynamic.

A single season-wide network may hide important changes in role, linemate structure, strategy, injuries, coaching, and game state.

The project will therefore consider temporal networks at multiple levels, potentially including:

* individual possessions,
* individual games,
* rolling game windows,
* monthly periods,
* full seasons,
* even-strength play,
* power plays,
* penalty kills,
* offensive-zone possessions,
* defensive-zone breakouts,
* and neutral-zone transitions.

This will allow us to study both stable network roles and short-term changes.

### 9. Passing Motifs

Beyond traditional centrality measures, the project may investigate recurring passing motifs.

A motif is a small network pattern that appears repeatedly.

For example:

```text
Player A -> Player B -> Player C
```

or:

```text
Player A -> Player B
    ^          |
    |          v
Player C <-----
```
Repeated three-player structures may help identify:

* power-play patterns,
* breakout structures,
* cycling behavior,
* transition combinations,
* or recurring tactical relationships.

This is particularly interesting because similar motif-based approaches have been used in soccer passing-network research.

### 10. Existing Computer-Vision Work

A related project has been exploring puck tracking from broadcast hockey video using object detection and computer vision.

The longer-term vision is not simply to detect the puck.

The goal is to reconstruct puck movement between players and convert those movement sequences into structured hockey events.

That would eventually make it possible to identify:

* puck possession changes,
* passing sequences,
* receptions,
* recoveries,
* zone transitions,
* and player interaction networks

directly from game video.

Previous puck-tracking experiments have already suggested an important practical distinction.

The model performs relatively well during stable broadcast sequences in which player positions are clear and the puck is moving between established players.

It struggles more during transient or uncertain sequences, particularly when stick blades create false positives or the puck is briefly occluded.

That work remains an important longer-term direction, but the capstone will not depend on solving the full computer-vision problem first.

Structured event-level passing data will be used whenever possible so that the primary capstone focus can remain on network science and hockey analysis.

## Project Phases

### Phase 1 - Build a Trustworthy ETL Pipeline

Acquire, inspect, validate, normalize, and document the event-level passing data.

Key requirements include:

* reliable player identities,
* consistent game identifiers,
* coordinate validation,
* event ordering,
* strength-state validation,
* missing-data handling,
* reproducible transformations,
* and source-level quality checks.

The objective is to create a trustworthy event table that can support all downstream network analysis.

### Phase 2 - Reconstruct Player and Linemate Relationships

Join event-level passing data to the existing historical player database.

Reconstruct:

* passer-receiver relationships,
* on-ice player combinations,
* linemate structures,
* possession participants,
* and team-specific player relationships.

This stage establishes the nodes and edges required for network construction.

### Phase 3 - Construct Temporal Networks

Build networks at multiple levels of aggregation.

Potential windows include:

* possession,
* game,
* rolling game windows,
* season,
* strength state,
* offensive-zone sequence,
* breakout sequence,
* zone-entry sequence,
* and special-teams situations.

This stage will allow the project to distinguish persistent network structure from short-term tactical variation.

### Phase 4 - Calculate Network Measures

Candidate network measures include:

* degree
* weighted degree
* PageRank
* HITS
* betweenness
* closeness
* clustering
* density
* reciprocity
* community structure
* motifs

Spatial-network measures will also be developed for puck movement between rink regions.

NetworkX will be the initial Python framework for graph construction and analysis.

### Phase 5 - Join Network Features to Existing Hockey Outcomes

Network-derived features will be joined back to the historical player database.

Potential comparison variables include:

* Corsi
* shot-attempt differential
* offensive production
* role
* position
* team
* strength state
* linemate combinations
* and team performance

This stage will test whether network-derived features add information beyond conventional hockey statistics.

### Phase 6 - Compare Results with Prior Corsi Research

The final stage will ask whether the network results:

* reproduce prior findings,
* explain previously observed relationships,
* contradict them,
* or extend them with information unavailable from Corsi alone.

The goal is not to replace Corsi.

The goal is to understand what network structure adds.

### Data Acquisition Strategy

The preferred capstone dataset is historical NHL event-level passing data with coordinates.

Current outreach has been initiated with:

* All Three Zones
* Stathletes
* Sportlogiq / Teamworks

The required fields are:

* passer,
* receiver,
* pass-start x/y,
* pass-end x/y,
* event time or order,
* game context,
* and preferably strength state.

Commercial or research access is still being evaluated.

### Fallback Data Strategy

The capstone should not depend entirely on a commercial vendor responding.

Public Stathletes Big Data Cup datasets are being evaluated as a fallback source.

These datasets may provide:

* pass events,
* player identities,
* intended receivers,
* start coordinates,
* end coordinates,
* event context,
* and in some cases tracking data.

If historical NHL-wide data cannot be secured immediately, the methodology can still be developed and validated using elite hockey event data.

The analytical framework will therefore be designed so that the data source can change without requiring the entire project to be redesigned.

### Project Architecture

Conceptually, the project consists of three layers:

```text
EXISTING PLAYER DATA
player_id
season
team
position
Corsi / possession metrics
historical attributes
        |
        | player_id
        v

PASS EVENT DATA
game_id
period
time / sequence
passer_id
receiver_id
start_x
start_y
end_x
end_y
strength_state
        |
        v

NETWORK / SPATIAL FEATURES
player centrality
passing pairs
motifs
breakout paths
zone-entry paths
transition networks
spatial hubs
dangerous-area progression
        |
        v

COMPARISON / MODELING
Corsi
production
team outcomes
role
strength state
linemate structure
```

### Longer-Term Direction

The long-term goal is to create a framework capable of linking:

```text
video
  ->
puck / player tracking
  ->
structured event data
  ->
possession sequences
  ->
player and spatial networks
  ->
hockey outcomes
```

That would make it possible to evaluate not only what happened on the ice, but how players and teams created those outcomes through connected sequences of puck movement.

Potential future applications include:

* player evaluation,
* line-combination analysis,
* trade-deadline analysis,
* team-style profiling,
* player archetypes,
* tactical comparisons,
* possession modeling,
* power-play structure,
* breakout evaluation,
* and automated hockey video analysis.

### Methodological Caution

The project will distinguish carefully between:

* descriptive network structure,
* statistical association,
* explanatory value,
* predictive value,
* and causal claims.

Network measures such as PageRank, HITS, degree, or betweenness should not be interpreted as causes of player or team production.

Instead, they will be evaluated as structural features that may help explain or predict hockey outcomes when combined with conventional variables.

### Current Status

### Current Status

- [x] Project concept defined
- [x] New repository initialized
- [x] Python virtual environment created
- [x] Initial project structure created
- [x] Existing historical player database identified as an upstream asset
- [x] Passing-network literature direction established
- [x] Minimum event-level data requirements defined
- [x] Commercial data-provider outreach initiated
- [ ] Evaluate public Stathletes Big Data Cup data
- [ ] Confirm primary event-data source
- [ ] Update historical player database with latest NHL season
- [ ] Finalize canonical event schema
- [ ] Build initial ETL pipeline
- [ ] Construct first player passing network
- [ ] Construct first spatial puck-movement network
- [ ] Join network features to historical Corsi data
- [ ] Begin temporal and tactical network analysis

### Immediate Next Steps

1. Evaluate the public Stathletes dataset as a fallback data source.
2. Document the exact pass-event schema.
3. Confirm coordinate orientation and rink dimensions.
4. Define canonical player and game identifiers.
5. Update the historical player database with the latest NHL season.
6. Build a one-game ETL prototype.
7. Construct the first player-to-player passing graph.
8. Construct the first spatial transition graph.
9. Compare initial network measures with existing player possession metrics.

### Repository Structure

Planned structure:

```text
nhl-passing-networks/
│
├── README.md
├── AGENTS.md
├── pyproject.toml
├── .gitignore
│
├── data/
│   ├── raw/
│   │   ├── passing/
│   │   └── player_master/
│   ├── interim/
│   └── processed/
│
├── docs/
│   ├── project_scope.md
│   ├── data_requirements.md
│   ├── literature_review.md
│   └── vendor_outreach.md
│
├── notebooks/
│   ├── 01_data_inventory.ipynb
│   ├── 02_player_network.ipynb
│   ├── 03_spatial_network.ipynb
│   └── 04_transition_analysis.ipynb
│
├── src/
│   ├── ingest/
│   ├── identity/
│   ├── networks/
│   ├── spatial/
│   └── visualization/
│
├── tests/
│
└── references/
    └── papers/
```

### Summary

The project begins with a simple idea:

Hockey outcomes emerge from connected sequences of player interaction and puck movement.

Traditional metrics such as Corsi describe important outcomes of those sequences.

Network analysis offers a way to study the structure that produced them.

By combining historical player data, event-level passing information, spatial coordinates, and network-science methods, this project will investigate whether hockey possession and offensive creation can be understood more deeply as a connected system rather than as a collection of independent events.






