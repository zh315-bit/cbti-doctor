# V1 vs V1.1 Failure Analysis

V1.1 first frozen run preserved historical V1 failures and introduced no observed critical failure in the offline review. The dominant persisted issue is over-asking: explicit query facts were not reliably extracted by the model-facing run, so many ASK paths remained. Diary DA-04/DA-08 projection contradictions were not observed in the V1.1 final traces; this is marked resolved for this run, not generalized. Attribution for score changes is `combined_effect` where extraction, sufficiency, and grounding interact.

Historical status: repeated ASK = persists; State-integrity omissions = persists in stochastic traces; PD repeated ASK = persists; diary projection contradiction = resolved in this run; unsupported answer claims = no observed critical failure. New-failure checks found no premature-answer, unavailable-resource-as-real, stale-fact, or provenance-mismatch critical failure.
