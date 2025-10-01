# Predict.Dl

Predict.Dl is a small Discord bot and toolkit for Deadlock that calculates a Player Rating (PR)
from detailed per-hero statistics and displays it in Discord with rank emojis.

I'm still working on it and trying to make it better and more accurate, with the end goal of being able to predict matches.

Roadmap
--------
- Add a better PR calculation that takes the other player's rank and performace into account because right now PR is very untuned and not usable.

Features
--------
- /lookup command: resolve a Steam ID or vanity name, fetch hero stats, and show a PR with a per-hero breakdown.
- PR calculation: multi-factor scoring using damage, objective damage, K/D/A rates, accuracy, level, networth, and wins.
- Recency-aware: more recent games have higher influence via exponential decay (configurable half-life).
- Confidence weighting: heroes with more matches are weighted higher (sqrt scaling by default).
- Rank calibration: if a player's rank is known (from the API), PR can be nudged toward a rank-implied value so ranks map consistently.

PR calculation breakdown
------------------------
The algorithm (see `api.calcPr`) is intentionally small and tweakable. Here's the summary of the steps:

1. Input: list of hero-stat dictionaries. Example fields used:
	- matches_played, wins, last_played (unix timestamp)
	- kills_per_min, deaths_per_min, assists_per_min
	- networth_per_min, damage_per_min, obj_damage_per_min
	- accuracy, crit_shot_rate, ending_level

2. Per-feature normalization
	- For each feature (e.g. damage_per_min) we compute the player's maximum across their heroes and divide each hero's value by that max. This creates 0..1 normalized feature values per hero.

3. Weighted feature sum
	- Each normalized feature is multiplied by a weight (see `params` in `api.calcPr`), and summed to a raw per-hero score.
	- Example weights are: w_win, w_kills, w_assists, w_deaths (inverted), w_damage, w_obj, w_accuracy, etc.

4. Hero confidence weight
	- Each hero's score is multiplied by a confidence weight = recency_weight * match_confidence
	- recency_weight is exponential decay: 0.5^(age / half_life_seconds). Default half-life is 90 days.
	- match_confidence is sqrt(matches_played) by default (scaled by `match_confidence_scale` param).

5. Aggregation
	- The final normalized overall score is the weighted average of hero scores by their confidence weight.

6. PR scaling
	- The normalized overall score (0..1) is scaled to a PR range. Defaults in the code: `pr_per_tier = 100` and `max_pr_tiers = 66`, resulting in a 0..6600 PR range.
	- By convention in this repo: every 100 PR points equals one rank tier (Initiate 1 → Eternus 6).

7. Optional rank calibration
	- If a `player_rank` hint is provided (from API: `rank` tier or `player_score`), `calcPr` blends the computed PR toward a target PR implied by that rank. The blending magnitude is controlled by `rank_confidence`.

Why this design?
-----------------
- Per-player normalization (max across heroes) reduces the effect of absolute scale differences between different hero roles.
- Confidence weighting prevents noisy, low-sample heroes from dominating overall PR.
- Recency decay ensures old games don't lock a player permanently to a bad/good score.
- Rank calibration keeps PR consistent with externally-sourced rank info and avoids rank/PR contradictions.

Tweakable knobs
----------------
- `recency_half_days` (default 90)
- `match_confidence_scale` (default 1.0)
- Feature weights: `w_win`, `w_kills`, `w_assists`, `w_deaths`, `w_networth`, `w_damage`, `w_obj`, `w_accuracy`, `w_crit`, `w_level`
- PR scaling: `pr_per_tier` (default 100), `max_pr_tiers` (default 66)
- `rank_confidence` when calling `calcPr` to control how strongly PR is pulled toward a known rank
