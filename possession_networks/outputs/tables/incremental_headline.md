Primary setting: whole match features, grouped 10 fold CV repeated 10 times, strict open xT chain, open play networks. Cells are the change in out of fold R2 with a 95% paired bootstrap interval over matches.

| Target | Baseline | Baseline R2 | + network | + xT | + both |
|---|---|---|---|---|---|
| gd | corsi | 0.091 | +0.167 [+0.103, +0.234] | +0.103 [+0.054, +0.155] | +0.235 [+0.168, +0.304] |
| gd | corsi_sot | 0.382 | +0.053 [+0.015, +0.095] | +0.022 [-0.005, +0.050] | +0.072 [+0.029, +0.117] |
| gd | corsi_xg | 0.407 | +0.089 [+0.042, +0.137] | +0.030 [+0.005, +0.057] | +0.101 [+0.053, +0.152] |
| gd | corsi_vol | 0.084 | +0.173 [+0.109, +0.238] | +0.110 [+0.060, +0.162] | +0.241 [+0.174, +0.311] |
| xgd | corsi | 0.517 | +0.007 [-0.019, +0.033] | +0.080 [+0.040, +0.121] | +0.085 [+0.040, +0.130] |
| xgd | corsi_sot | 0.589 | -0.012 [-0.025, +0.002] | +0.047 [+0.019, +0.076] | +0.038 [+0.005, +0.070] |
| xgd | corsi_vol | 0.516 | +0.009 [-0.016, +0.035] | +0.083 [+0.042, +0.125] | +0.087 [+0.042, +0.132] |

Same events versus disjoint events (target goal difference, baseline corsi):

| Window (features to target) | Baseline R2 | + network | + xT | + both |
|---|---|---|---|---|
| Primary: whole match, grouped CV | 0.091 | +0.167 [+0.103, +0.234] | +0.103 [+0.054, +0.155] | +0.235 [+0.168, +0.304] |
| Window: half 1 to half 1 | 0.107 | +0.000 [-0.027, +0.028] | +0.031 [-0.004, +0.065] | +0.032 [-0.009, +0.073] |
| Window: half 2 to half 2 | 0.095 | +0.065 [+0.009, +0.120] | +0.041 [-0.001, +0.078] | +0.080 [+0.019, +0.139] |
| Window: level score to full time | 0.079 | +0.042 [-0.013, +0.098] | +0.016 [-0.004, +0.036] | +0.056 [+0.000, +0.113] |
| Window: half 1 to half 2 (disjoint) | 0.032 | -0.007 [-0.032, +0.018] | -0.000 [-0.013, +0.014] | -0.003 [-0.027, +0.021] |
