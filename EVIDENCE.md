# Evidence

## Stage 12 — Evaluation

The AI Image Understanding & Content Matching Engine was evaluated using a
10-case labeled evaluation dataset.

### Evaluation Results

```text
======================================================================
AI IMAGE MATCHING EVALUATION
======================================================================

[PASS] fox_match
       Expected subject: fox
       Actual subject:   fox
       Similarity: 0.8107
       Confidence: 0.9
       Accepted: True

[PASS] wolf_match
       Expected subject: wolf
       Actual subject:   wolf
       Similarity: 0.8117
       Confidence: 0.9
       Accepted: True

[PASS] lion_match
       Expected subject: lion
       Actual subject:   Lion
       Similarity: 0.7911
       Confidence: 0.8
       Accepted: True

[PASS] fox_wolf_mismatch
       Wrong subject tested: wolf
       Similarity: 0.7477
       Confidence: 0.9
       Accepted: False
       Guard reason: Image subject "wolf" does not match expected subject "fox".

[PASS] fox_lion_mismatch
       Wrong subject tested: Lion
       Similarity: 0.6831
       Confidence: 0.8
       Accepted: False
       Guard reason: Similarity score 0.683 is below the required threshold of 0.700.

[PASS] wolf_fox_mismatch
       Wrong subject tested: fox
       Similarity: 0.6784
       Confidence: 0.9
       Accepted: False
       Guard reason: Similarity score 0.678 is below the required threshold of 0.700.

[PASS] lion_fox_mismatch
       Wrong subject tested: fox
       Similarity: 0.6689
       Confidence: 0.9
       Accepted: False
       Guard reason: Similarity score 0.669 is below the required threshold of 0.700.

[PASS] low_confidence_organ_pipe
       Image ID: 4
       Subject: organ pipe
       Similarity: 0.8524
       Confidence: 0.6
       Accepted: False
       Guard reason: Image confidence 0.600 is below the required threshold of 0.700.

[PASS] dog_no_confident_match
       Accepted matches: 0
       Expected: no confident match

[PASS] cat_no_confident_match
       Accepted matches: 0
       Expected: no confident match

======================================================================
EVALUATION SUMMARY
======================================================================
Top-1 Precision: 3/3 = 100.00%
Mismatch Guard: 4/4 passed
Low-Confidence Guard: 1/1 passed
No-Confident-Match: 2/2 passed
Overall: 10/10 tests passed
======================================================================