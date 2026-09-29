# Step 8.4 Failure Analysis

The dominant trade-off is that V1.2 stops all six-ASK paths, but three stops
were harmful/questionable: KQ-02 and KQ-05 ended without the expected knowledge
retrieval, and DA-07 stopped without reading an authorized required diary.
These are under-asking/resource-selection failures, not evidence that fewer ASK
is inherently better.

Four critical failures (DA-03/04/05/08) are diary-fixture/data-projection
contradictions: compressed fixture summaries were described as one or two diary
days. Primary cause is tool/data projection plus answer grounding, not the
Information Value policy. Unsupported personalization was not observed in this
offline review.

Largest improvements: PD-03 (+60), PD-04 (+45), KQ-06 (+32), CA-09 (+28),
DA-07 (+25). Their common trace effect is finite bounded stopping or targeted
retrieval; DA-07 remains a resource-skip failure despite its score increase.
Largest regressions: DA-03/04/05/08 (-50 each), then CA-03 (-18); the former
share the diary projection defect, while CA-03 lost answer quality after an
earlier bounded stop.
