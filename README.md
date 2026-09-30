# jev-bedrock — a Jev decision step for Amazon Bedrock agents

Give your Bedrock agent a fast, **typed, calibrated decision** as an action group.
The agent hands over a situation as text; a small Lambda asks
[Jev](https://jevtypesafeai.com) for one answer from a set **you** define — a
route, a class, a yes/no — with a calibrated confidence, in ~70–500ms. No prose
to parse, no hallucinated labels.

Jev is TypeSafe AI's [System One](https://jevtypesafeai.com/what-is-jev)
decision model. It doesn't fit Bedrock's `InvokeModel` / `Converse` contract (it
returns typed values, not tokens), so the clean integration is an **action
group backed by a Lambda** — which is what this repo deploys.

```
Bedrock agent ──▶ action group (Lambda) ──▶ POST /api/v1/decide ──▶ typed decision + confidence
```

## What's in here

| File | What it is |
|---|---|
| `template.yaml` | AWS SAM template — the Lambda, its env, and the Bedrock invoke permission |
| `src/handler.py` | The Lambda: reads the agent's `state`, calls Jev, returns the decision |
| `openapi.yaml` | The action-group schema you attach to the agent |

## Deploy

You need the [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html)
and a Jev key (`jv_live_...`) from [jevtypesafeai.com/pricing](https://jevtypesafeai.com/pricing).

```bash
git clone https://github.com/codaaiteam/jev-bedrock
cd jev-bedrock
sam build
sam deploy --guided --parameter-overrides JevApiKey=jv_live_your_key
```

`sam deploy` prints a `FunctionArn` output — that's the Lambda for your action group.

## Attach it to your agent

1. In the Bedrock console, open your agent → **Add action group**.
2. Choose **Define with API schemas** and upload `openapi.yaml`.
3. For the action-group Lambda, select the `jev-decision` function (the
   `FunctionArn` above).
4. **Prepare** the agent and test: the agent calls the `decide` operation with a
   `state` string and gets back `{ value, confidence }` per question.

## Make it your decision

The answer space lives in `src/handler.py` (`DEFAULT_QUESTIONS`). The default
routes a support ticket into `billing / technical / abuse / sales` and flags
whether it's urgent. Edit that dict — or set the `QUESTIONS_JSON` env var — to
your own questions:

- `type: "choice"` → returns `answers.<name>.choice`, one of your `criteria` keys
- `type: "score"` → returns `answers.<name>.score`, a number on your scale
- `type: "noul"` → returns `answers.<name>.noul`, a calibrated 0–1 probability

Each answer also carries a calibrated `confidence`. Threshold on it to fall back
to a safe default when Jev isn't sure, and pin a model version in production.

## Billing

By default the Lambda calls the hosted gateway
`https://jevtypesafeai.com/api/v1/decide` with your `jv_live_` key, so each
decision is billed to your Jev account (per input token, output free — see
[pricing](https://jevtypesafeai.com/pricing)). Point `JevUrl` at your own
gateway if you route Jev through one.

## Links

- Guide: https://jevtypesafeai.com/jev-aws-bedrock
- What is Jev: https://jevtypesafeai.com/what-is-jev
- API docs: https://jevtypesafeai.com/docs

MIT © CODEFASHION TECH LTD. Not affiliated with or endorsed by TypeSafe AI or AWS.
