# Submission

Fork URL: <!-- paste the URL of your fork here -->

## Files to commit

- [ ] `notes.md` with your commands (optional)

## Questions

Answer in your own words. Where a question asks for output, paste it in a code block.

### Q1. Paste your two metric filters (pattern, metric name, namespace, value). Why can CloudWatch turn a log line into a metric, and what does a metric filter NOT do for log lines that arrived before it existed?

**Your answer:**

<!-- replace this line with your answer -->

### Q2. Paste your alarm definition. Explain period, evaluation periods and datapoints to alarm in your own words: why 3 of 3 one-minute datapoints and not 1 of 1? What does it trade (speed against false alarms)?

**Your answer:**

<!-- replace this line with your answer -->

### Q3. What is `TreatMissingData`? In this lab the filters publish nothing when there are no matching lines; which setting did you choose and what would happen to your alarm at 3 a.m. with each of the other settings?

**Your answer:**

<!-- replace this line with your answer -->

### Q4. Why is an alarm on the error RATE (errors divided by requests) better than an alarm on the error COUNT? Show the metric-math expression and a situation where the count alone would mislead.

**Your answer:**

<!-- replace this line with your answer -->

### Q5. Paste the alarm history lines that show your alarm going to ALARM and the SNS action being executed, and later back to OK. How long after you raised the error rate did it fire, and which three numbers (period, datapoints, publication delay) explain it?

**Your answer:**

<!-- replace this line with your answer -->

### Q6. Describe your dashboard: which widgets, which period, which statistic, and one decision it helps an on-call engineer make in ten seconds. Why put the alarm status on the dashboard?

**Your answer:**

<!-- replace this line with your answer -->

### Q7. Paste the output of `./verify.sh`. It must end with **ALL CHECKS PASSED**.

**Your answer:**

<!-- replace this line with your answer -->

### Q8. **Tear down.** Paste the output of `./verify-teardown.sh`. It must end with **TEARDOWN VERIFIED**.

**Your answer:**

<!-- replace this line with your answer -->
