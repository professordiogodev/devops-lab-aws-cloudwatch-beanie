#!/usr/bin/env bash
# Creates the emitter: a Lambda function that runs once a minute and logs 60 JSON requests. Run once: ./setup.sh
set -u
cd "$(dirname "$0")"
L=aws-cloudwatch-beanie
aws sts get-caller-identity >/dev/null 2>&1 || { echo "No working AWS credentials." >&2; exit 1; }
ACCT=$(aws sts get-caller-identity --query Account --output text)
REGION=$(aws configure get region); REGION=${AWS_REGION:-${AWS_DEFAULT_REGION:-${REGION:-us-east-1}}}
if aws lambda get-function --function-name beanie-emitter >/dev/null 2>&1; then echo "The emitter already exists."; exit 0; fi
python3 - <<'PY'
import zipfile
with zipfile.ZipFile("emitter.zip", "w", zipfile.ZIP_DEFLATED) as z:
    z.write("emitter/handler.py", "handler.py")
PY
aws ssm put-parameter --name /beanie-lab/error-rate --type String --value 0 --overwrite --tags Key=lab,Value=$L >/dev/null 2>&1 || aws ssm put-parameter --name /beanie-lab/error-rate --type String --value 0 --overwrite >/dev/null
aws iam create-role --role-name beanie-emitter-role --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"lambda.amazonaws.com"},"Action":"sts:AssumeRole"}]}' --tags Key=lab,Value=$L >/dev/null
aws iam attach-role-policy --role-name beanie-emitter-role --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
aws iam put-role-policy --role-name beanie-emitter-role --policy-name read-error-rate --policy-document "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Action\":\"ssm:GetParameter\",\"Resource\":\"arn:aws:ssm:$REGION:$ACCT:parameter/beanie-lab/error-rate\"}]}"
sleep 12
aws lambda create-function --function-name beanie-emitter --runtime python3.12 --handler handler.lambda_handler --role arn:aws:iam::$ACCT:role/beanie-emitter-role \
  --zip-file fileb://emitter.zip --timeout 20 --memory-size 128 --tags lab=$L >/dev/null || { echo "could not create the function (the role may need a few more seconds: run ./setup.sh again)"; exit 1; }
aws lambda wait function-active --function-name beanie-emitter
aws events put-rule --name beanie-emitter-every-minute --schedule-expression 'rate(1 minute)' --tags Key=lab,Value=$L >/dev/null
aws lambda add-permission --function-name beanie-emitter --statement-id events --action lambda:InvokeFunction --principal events.amazonaws.com --source-arn arn:aws:events:$REGION:$ACCT:rule/beanie-emitter-every-minute >/dev/null
aws events put-targets --rule beanie-emitter-every-minute --targets "Id=1,Arn=arn:aws:lambda:$REGION:$ACCT:function:beanie-emitter" >/dev/null
rm -f emitter.zip
cat <<TXT
The emitter is running: every minute it writes 60 JSON request lines to the log group /aws/lambda/beanie-emitter.
  Error rate right now: 0%   (change it with:  aws ssm put-parameter --name /beanie-lab/error-rate --type String --value 30 --overwrite)
The first log lines appear within two minutes. Region: $REGION.
TXT
