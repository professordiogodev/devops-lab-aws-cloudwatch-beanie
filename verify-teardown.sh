#!/usr/bin/env bash
# Proves the lab left nothing in AWS. Run with: ./verify-teardown.sh
set -u
ACCOUNT=$(aws sts get-caller-identity --query Account --output text 2>/dev/null) || { echo "No working AWS credentials." >&2; exit 1; }
echo "Checking account $ACCOUNT, region $(aws configure get region)"
pass=0; failn=0
check() { local d="$1"; shift; if "$@" >/dev/null 2>&1; then echo "PASS  $d"; pass=$((pass+1)); else echo "FAIL  $d"; failn=$((failn+1)); fi; }
empty() { local r; r=$(eval "$1" 2>/dev/null); [ -z "$r" ] || [ "$r" = None ]; }
check "no Lambda function beanie-emitter" bash -c '! aws lambda get-function --function-name beanie-emitter'
check "no schedule rule beanie-emitter-every-minute" bash -c '! aws events describe-rule --name beanie-emitter-every-minute'
check "no IAM role beanie-emitter-role" bash -c '! aws iam get-role --role-name beanie-emitter-role'
check "no SSM parameter /beanie-lab/error-rate" bash -c '! aws ssm get-parameter --name /beanie-lab/error-rate'
check "no log group /aws/lambda/beanie-emitter" empty "aws logs describe-log-groups --log-group-name-prefix /aws/lambda/beanie-emitter --query 'logGroups[].logGroupName' --output text"
check "no alarm whose name starts with beanie-" empty "aws cloudwatch describe-alarms --alarm-name-prefix beanie- --alarm-types CompositeAlarm MetricAlarm --query 'MetricAlarms[].AlarmName' --output text"
check "no dashboard named beanie" bash -c '! aws cloudwatch get-dashboard --dashboard-name beanie'
check "no SNS topic beanie-alerts" empty "aws sns list-topics --query \"Topics[?contains(TopicArn, ':beanie-alerts')].TopicArn\" --output text"
check "no saved Logs Insights query starting with beanie-" empty "aws logs describe-query-definitions --query \"queryDefinitions[?starts_with(name, 'beanie-')].name\" --output text"
echo
if [ "$failn" -eq 0 ]; then echo "TEARDOWN VERIFIED ($pass/$pass) in account $ACCOUNT"; else echo "NOT CLEAN: $failn leftover(s). Remove them and run this again."; fi
exit "$failn"
