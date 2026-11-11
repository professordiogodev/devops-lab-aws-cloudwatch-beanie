#!/usr/bin/env python3
import datetime, json, os, re, subprocess, sys, time
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
LG = "/aws/lambda/beanie-emitter"
ALARM = "beanie-error-rate-high"
passed = failed = 0


def check(desc, ok, hint=""):
    global passed, failed
    if ok:
        passed += 1; print("PASS  " + desc, flush=True)
    else:
        failed += 1; print("FAIL  " + desc + (("   -> " + hint) if hint else ""), flush=True)


def aws(*a):
    try:
        return json.loads(subprocess.check_output(("aws",) + a + ("--output", "json"), stderr=subprocess.DEVNULL, timeout=90) or "null")
    except Exception:
        return None


def finish():
    print()
    print(("ALL CHECKS PASSED (%d/%d)" % (passed, passed)) if failed == 0 else ("%d check(s) failed, %d passed" % (failed, passed)))
    sys.exit(1 if failed else 0)


def set_rate(v):
    subprocess.run(["aws", "ssm", "put-parameter", "--name", "/beanie-lab/error-rate", "--type", "String", "--value", str(v), "--overwrite"], capture_output=True)


def wait_for(fn, secs, step=15):
    end = time.time() + secs
    while time.time() < end:
        try:
            r = fn()
            if r:
                return r
        except Exception:
            pass
        time.sleep(step)
    return None


print("== The emitter and its logs ==")
fn = aws("lambda", "get-function", "--function-name", "beanie-emitter")
check("the emitter function exists (run ./setup.sh)", bool(fn))
if not fn:
    finish()
ev = wait_for(lambda: (aws("logs", "filter-log-events", "--log-group-name", LG, "--limit", "1") or {}).get("events"), 150)
check("its log group has events", bool(ev))
lg = (aws("logs", "describe-log-groups", "--log-group-name-prefix", LG) or {}).get("logGroups", [])
lg = next((g for g in lg if g["logGroupName"] == LG), {})
check("the log group keeps logs for 7 days (not forever)", lg.get("retentionInDays") == 7, "retention is %s" % lg.get("retentionInDays"))

print("== Logs to metrics ==")
mf = (aws("logs", "describe-metric-filters", "--log-group-name", LG) or {}).get("metricFilters", [])
by_metric = {t["metricName"]: (f, t) for f in mf for t in f.get("metricTransformations", [])}
check("a metric filter publishes RequestCount in the namespace Beanie (value 1 per matching line)", "RequestCount" in by_metric and by_metric["RequestCount"][1]["metricNamespace"] == "Beanie" and by_metric["RequestCount"][1]["metricValue"] == "1")
check("a metric filter publishes ErrorCount in the namespace Beanie", "ErrorCount" in by_metric and by_metric["ErrorCount"][1]["metricNamespace"] == "Beanie")
if "ErrorCount" in by_metric:
    pat = by_metric["ErrorCount"][0].get("filterPattern", "")
    check("the ErrorCount pattern selects failures by status (>= 500) or level, in JSON syntax (%s)" % pat, bool(re.search(r"\$\.status\s*>=?\s*5\d\d|\$\.level\s*=\s*\"?error", pat)))
check("the metrics receive data (RequestCount in the last 15 minutes)", bool(wait_for(lambda: [d for d in (aws("cloudwatch", "get-metric-statistics", "--namespace", "Beanie", "--metric-name", "RequestCount", "--start-time", (datetime.datetime.utcnow() - datetime.timedelta(minutes=15)).strftime("%Y-%m-%dT%H:%M:%SZ"), "--end-time", datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"), "--period", "60", "--statistics", "Sum") or {}).get("Datapoints", []) if d["Sum"] > 0], 240)))

print("== Notification, alarm, dashboard ==")
topics = [t["TopicArn"] for t in (aws("sns", "list-topics") or {}).get("Topics", []) if t["TopicArn"].endswith(":beanie-alerts")]
check("an SNS topic named beanie-alerts exists", len(topics) == 1)
al = (aws("cloudwatch", "describe-alarms", "--alarm-names", ALARM) or {}).get("MetricAlarms", [])
a = al[0] if al else {}
check("an alarm named %s exists" % ALARM, bool(a), "aws cloudwatch put-metric-alarm ...")
if a:
    exprs = [m for m in a.get("Metrics", []) if m.get("Expression")]
    check("it is a metric-math alarm: an expression divides ErrorCount by RequestCount (an error RATE, not a count)", bool(exprs) and "/" in exprs[0]["Expression"] and any("ErrorCount" in json.dumps(m) for m in a["Metrics"]) and any("RequestCount" in json.dumps(m) for m in a["Metrics"]), str([m.get("Expression") for m in a.get("Metrics", [])]))
    check("the threshold is between 1 and 20 percent and the operator is 'greater than'", a.get("ComparisonOperator", "").startswith("GreaterThan") and 1 <= a.get("Threshold", 0) <= 20, "%s %s" % (a.get("ComparisonOperator"), a.get("Threshold")))
    check("it needs several datapoints (3 evaluation periods, at least 2 breaching) of one-minute periods", a.get("EvaluationPeriods", 0) >= 3 and a.get("DatapointsToAlarm", a.get("EvaluationPeriods", 0)) >= 2 and all(m.get("Period", 60) == 60 for m in a.get("Metrics", []) if m.get("MetricStat")))
    check("missing data does not raise the alarm (TreatMissingData notBreaching)", a.get("TreatMissingData") == "notBreaching", str(a.get("TreatMissingData")))
    check("the alarm notifies the topic when it fires AND when it recovers", bool(topics) and topics[0] in a.get("AlarmActions", []) and topics[0] in a.get("OKActions", []))
d = aws("cloudwatch", "get-dashboard", "--dashboard-name", "beanie")
widgets = json.loads(d["DashboardBody"]).get("widgets", []) if d else []
check("a dashboard named beanie with at least 4 widgets", len(widgets) >= 4, "aws cloudwatch put-dashboard")
body = json.dumps(widgets)
check("it shows the request count, the error rate (a metric-math expression) and the alarm", "RequestCount" in body and "ErrorCount" in body and ("alarm" in body.lower()) and ("/" in body))
qd = [q for q in (aws("logs", "describe-query-definitions") or {}).get("queryDefinitions", []) if q["name"].startswith("beanie-")]
check("a saved Logs Insights query whose name starts with beanie- (and which filters or aggregates)", bool(qd) and any(re.search(r"stats|filter|sort", q["queryString"]) for q in qd))

print("== Raise the error rate and wait for the alarm (about 8 minutes) ==")
t0 = time.time()
try:
    set_rate(60)
    got = wait_for(lambda: ((aws("cloudwatch", "describe-alarms", "--alarm-names", ALARM) or {}).get("MetricAlarms") or [{}])[0].get("StateValue") == "ALARM", 840, 20)
    check("with 60%% of requests failing, the alarm goes to ALARM (took %d s)" % (time.time() - t0), bool(got), "state is " + str((((aws("cloudwatch", "describe-alarms", "--alarm-names", ALARM) or {}).get("MetricAlarms") or [{}])[0]).get("StateValue")))
    hist = aws("cloudwatch", "describe-alarm-history", "--alarm-name", ALARM, "--history-item-type", "Action", "--max-records", "10") or {}
    check("the alarm history shows the SNS action was executed", any("Successfully executed action" in h.get("HistorySummary", "") and "sns" in h.get("HistorySummary", "") for h in hist.get("AlarmHistoryItems", [])), "check the alarm actions and the topic")
finally:
    set_rate(0)
t1 = time.time()
got = wait_for(lambda: ((aws("cloudwatch", "describe-alarms", "--alarm-names", ALARM) or {}).get("MetricAlarms") or [{}])[0].get("StateValue") == "OK", 840, 20)
check("after the error rate is back to 0%%, the alarm returns to OK (took %d s)" % (time.time() - t1), bool(got))
finish()
