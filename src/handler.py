"""Bedrock action-group Lambda: a Jev decision step.

The agent hands over the current situation as text; this function asks Jev for a
typed, calibrated decision and hands the answer back. The *answer space* is
yours — defined once in DEFAULT_QUESTIONS below (or via the QUESTIONS_JSON env
var), never inferred by the agent.

Calls the hosted gateway at jevtypesafeai.com with a jv_live_ key by default, so
every decision is billed through your Jev account.
https://jevtypesafeai.com/jev-aws-bedrock
"""

import json
import os
import urllib.request

JEV_URL = os.environ.get("JEV_URL", "https://jevtypesafeai.com/api/v1/decide")
JEV_API_KEY = os.environ["JEV_API_KEY"]  # jv_live_... from jevtypesafeai.com/pricing

# Your answer space. Edit this — or set QUESTIONS_JSON — to fit your decision.
# type "choice" → answers.<name>.choice (one of your criteria keys)
# type "score"  → answers.<name>.score  (a number on your scale)
# type "noul"   → answers.<name>.noul   (a calibrated 0–1 probability)
DEFAULT_QUESTIONS = {
    "queue": {
        "type": "choice",
        "instructions": "Which queue should this ticket go to?",
        "criteria": {
            "billing": "payments, refunds, invoices",
            "technical": "bugs, errors, how-to",
            "abuse": "spam, fraud, policy violations",
            "sales": "pricing, upgrades, new purchases",
        },
    },
    "urgent": {
        "type": "noul",
        "instructions": "Does this need a human within the hour?",
    },
}

QUESTIONS = (
    json.loads(os.environ["QUESTIONS_JSON"])
    if os.environ.get("QUESTIONS_JSON")
    else DEFAULT_QUESTIONS
)


def _state_from_event(event):
    """Bedrock passes the caller's text as a requestBody property or a parameter."""
    content = (event.get("requestBody") or {}).get("content", {})
    for prop in content.get("application/json", {}).get("properties", []):
        if prop.get("name") == "state":
            return prop.get("value", "")
    for param in event.get("parameters", []):
        if param.get("name") == "state":
            return param.get("value", "")
    return event.get("inputText", "")


def _decide(state):
    payload = json.dumps({"state": state, "questions": QUESTIONS}).encode()
    req = urllib.request.Request(
        JEV_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {JEV_API_KEY}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())["answers"]


def _flatten(answers):
    """Reduce each typed answer to {value, confidence} the agent can branch on."""
    out = {}
    for name, a in answers.items():
        if "choice" in a:
            value = a["choice"]
        elif "noul" in a:
            value = a["noul"]
        elif "score" in a:
            value = a["score"]
        else:
            out[name] = a
            continue
        out[name] = {"value": value, "confidence": a.get("confidence")}
    return out


def lambda_handler(event, context):
    answers = _decide(_state_from_event(event))
    body = json.dumps(_flatten(answers))
    return {
        "messageVersion": "1.0",
        "response": {
            "actionGroup": event.get("actionGroup", "JevDecision"),
            "apiPath": event.get("apiPath", "/decide"),
            "httpMethod": event.get("httpMethod", "POST"),
            "httpStatusCode": 200,
            "responseBody": {"application/json": {"body": body}},
        },
    }
