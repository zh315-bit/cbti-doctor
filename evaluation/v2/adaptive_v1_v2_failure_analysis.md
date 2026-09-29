# Step 6.1 Failure Analysis

The main natural V2 failure is repeated ASK: 13 cases ended in `ASK` after six
turns, including 10/12 personalized-decision cases. It made 111 asks: 19
necessary/useful (17.1%), 80 redundant (72.1%), and 12 irrelevant (10.8%). The
primary cause is `decision_policy`; missing explicit facts/merge may be a
downstream state-integrity effect but is not double-counted without a direct
trace omission.

Two critical failures are recorded: DA-04 and DA-08 said the diary had two and
one day while their fixtures represented a weekday/weekend split and 11
available entries. Primary cause is `tool_execution` / diary fixture projection;
downstream effect is an answer that contradicts diary data. This is a novel V2
failure mode. DA-06 correctly stated the unavailable-diary limitation; no
unavailable resource was treated as real data and no unsupported quantitative
medical threshold was found in reviewed final answers.

Language is observational, not causal: distributed/colloquial Chinese scored
48.14/53.89 versus brief Chinese 79.2, while also containing more multi-turn
and ambiguous tasks. Hard cases averaged 46.7 versus easy 69.0 and medium 69.85.
