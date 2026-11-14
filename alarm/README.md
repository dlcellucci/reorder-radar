# Failure alarm (n8n)

Two boxes that tell you the minute any automation breaks, instead of a customer telling you a week later.

I run about 20 n8n workflows for a farm's sales and ops. Before this, a broken one just stopped. A newsletter went out twice, a dashboard sat blank, and I found out by accident. Now any failed run sends me a Slack message with the workflow name, the step that broke, the error, and a link to the failed run.

## Set it up

1. In n8n, **Import from file** and pick `failure-alarm.n8n.json`.
2. Open **DM me in Slack**, pick your Slack credential, and replace `YOUR_SLACK_USER_ID` with your own Slack member ID (Slack profile > ... > Copy member ID).
3. Publish it.
4. In every workflow you care about: **Settings > Error workflow > Failure alarm**. Save.

## Check it works

Make a throwaway workflow with a Webhook trigger and a Code node that says `throw new Error('test')`. Point its error workflow at the alarm, publish it, and hit the webhook URL. You should get the Slack message within a minute. Then delete the test workflow.

## Where it can be wrong

- It only fires on **live** runs (schedules, webhooks, forms). Runs you start by hand in the editor don't trigger it.
- It catches runs that **fail**. A run that "succeeds" but does nothing useful (zero rows, an empty email) stays quiet.
- If a schedule never fires at all (n8n down, out of credits), nothing fails, so nothing alarms. You need a separate daily "did everything run?" check for that.
- If Slack itself is down, the alarm retries 3 times and then gives up.
