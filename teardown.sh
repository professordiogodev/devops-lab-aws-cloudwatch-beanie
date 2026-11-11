#!/usr/bin/env bash
# Removes everything this lab created, including what you built. Run with: ./teardown.sh
set -u
cd "$(dirname "$0")"
aws sts get-caller-identity >/dev/null 2>&1 || { echo "No working AWS credentials." >&2; exit 1; }
aws events remove-targets --rule beanie-emitter-every-minute --ids 1 >/dev/null 2>&1; aws events delete-rule --name beanie-emitter-every-minute >/dev/null 2>&1 && echo "deleted the schedule"
aws lambda delete-function --function-name beanie-emitter >/dev/null 2>&1 && echo "deleted the function"
aws iam delete-role-policy --role-name beanie-emitter-role --policy-name read-error-rate >/dev/null 2>&1
aws iam detach-role-policy --role-name beanie-emitter-role --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole >/dev/null 2>&1
aws iam delete-role --role-name beanie-emitter-role >/dev/null 2>&1 && echo "deleted the role"
aws ssm delete-parameter --name /beanie-lab/error-rate >/dev/null 2>&1 && echo "deleted the parameter"
for f in $(aws logs describe-metric-filters --log-group-name /aws/lambda/beanie-emitter --query 'metricFilters[].filterName' --output text 2>/dev/null); do aws logs delete-metric-filter --log-group-name /aws/lambda/beanie-emitter --filter-name "$f" && echo "deleted metric filter $f"; done
aws logs delete-log-group --log-group-name /aws/lambda/beanie-emitter >/dev/null 2>&1 && echo "deleted the log group"
A=$(aws cloudwatch describe-alarms --alarm-name-prefix beanie- --query 'MetricAlarms[].AlarmName' --output text); C=$(aws cloudwatch describe-alarms --alarm-types CompositeAlarm --alarm-name-prefix beanie- --query 'CompositeAlarms[].AlarmName' --output text)
[ -n "$A$C" ] && aws cloudwatch delete-alarms --alarm-names $A $C && echo "deleted alarms: $A $C"
aws cloudwatch delete-dashboards --dashboard-names beanie >/dev/null 2>&1 && echo "deleted the dashboard"
for t in $(aws sns list-topics --query "Topics[?contains(TopicArn, ':beanie-alerts')].TopicArn" --output text); do aws sns delete-topic --topic-arn "$t" && echo "deleted the topic"; done
for q in $(aws logs describe-query-definitions --query "queryDefinitions[?starts_with(name, 'beanie-')].queryDefinitionId" --output text); do aws logs delete-query-definition --query-definition-id "$q" >/dev/null && echo "deleted a saved query"; done
echo "Now run ./verify-teardown.sh"
