"""Strictly verify an exact AdVerify public result and its provenance."""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from pathlib import Path
from typing import Any


EXPECTED_TRUE_POSITIVES = {
    "camp_001": 1,
    "camp_002": 1,
    "camp_003": 1,
    "camp_004": 0,
    "camp_005": 0,
    "camp_006": 1,
    "camp_007": 1,
    "camp_008": 1,
    "camp_009": 1,
    "camp_010": 1,
    "camp_011": 2,
    "camp_012": 2,
    "camp_013": 0,
    "camp_014": 0,
    "camp_015": 1,
    "camp_016": 1,
    "camp_017": 1,
    "camp_018": 2,
    "camp_019": 0,
    "camp_020": 4,
}


def fail(message: str) -> None:
    raise SystemExit(f"Gate failed: {message}")


def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            fail(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def load_json(path: Path) -> Any:
    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=reject_duplicate_keys,
            parse_constant=lambda value: fail(f"non-finite number {value!r}"),
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        fail(f"cannot read strict JSON from {path}: {exc}")


def require_exact_float(value: Any, expected: float, name: str) -> None:
    if type(value) is not float or not math.isfinite(value) or value != expected:
        fail(f"{name}={value!r}, expected float {expected!r}")


def verify_results(results: Any, participant_id: str) -> None:
    if not isinstance(results, dict) or set(results) != {"participants", "results"}:
        fail(f"unexpected result document keys: {results!r}")

    expected_participants = {"anomaly_detector": participant_id}
    if results["participants"] != expected_participants:
        fail(f"participants={results['participants']!r}")

    assessments = results["results"]
    if not isinstance(assessments, list) or len(assessments) != 1:
        fail("expected exactly one assessment result")
    assessment = assessments[0]
    expected_keys = {
        "campaigns_evaluated",
        "avg_precision",
        "avg_recall",
        "avg_f1",
        "time_used",
        "campaign_results",
    }
    if not isinstance(assessment, dict) or set(assessment) != expected_keys:
        fail(f"unexpected assessment keys: {assessment!r}")
    if type(assessment["campaigns_evaluated"]) is not int:
        fail("campaigns_evaluated is not an integer")
    if assessment["campaigns_evaluated"] != 20:
        fail(f"campaigns_evaluated={assessment['campaigns_evaluated']!r}")
    for metric in ("avg_precision", "avg_recall", "avg_f1"):
        require_exact_float(assessment[metric], 1.0, metric)
    time_used = assessment["time_used"]
    if type(time_used) is not float or not math.isfinite(time_used):
        fail(f"time_used={time_used!r} is not a finite float")
    if not 0.0 < time_used < 3600.0:
        fail(f"time_used={time_used!r} is outside the workflow bound")

    campaigns = assessment["campaign_results"]
    if not isinstance(campaigns, dict):
        fail("campaign_results is not an object")
    if list(campaigns) != list(EXPECTED_TRUE_POSITIVES):
        fail(f"campaign identity or order mismatch: {list(campaigns)!r}")

    campaign_keys = {
        "precision",
        "recall",
        "f1",
        "true_positives",
        "false_positives",
        "false_negatives",
    }
    for campaign_id, expected_tp in EXPECTED_TRUE_POSITIVES.items():
        campaign = campaigns[campaign_id]
        if not isinstance(campaign, dict) or set(campaign) != campaign_keys:
            fail(f"unexpected {campaign_id} payload: {campaign!r}")
        for metric in ("precision", "recall", "f1"):
            require_exact_float(campaign[metric], 1.0, f"{campaign_id}.{metric}")
        for metric, expected in (
            ("true_positives", expected_tp),
            ("false_positives", 0),
            ("false_negatives", 0),
        ):
            value = campaign[metric]
            if type(value) is not int or value != expected:
                fail(f"{campaign_id}.{metric}={value!r}, expected {expected}")

    if sum(EXPECTED_TRUE_POSITIVES.values()) != 21:
        fail("internal expected true-positive total is not 21")


def verify_provenance(provenance: Any) -> None:
    if not isinstance(provenance, dict) or set(provenance) != {
        "image_digests",
        "timestamp",
        "github_actions",
    }:
        fail(f"unexpected provenance document: {provenance!r}")

    expected_digests = {
        "green-agent": os.environ["GREEN_IMAGE"],
        "anomaly_detector": os.environ["PARTICIPANT_IMAGE"],
        "agentbeats-client": os.environ["CLIENT_IMAGE"],
    }
    if provenance["image_digests"] != expected_digests:
        fail(f"image digests={provenance['image_digests']!r}")
    if not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z",
        provenance.get("timestamp", ""),
    ):
        fail(f"timestamp={provenance.get('timestamp')!r}")

    expected_actions = {
        "run_url": (
            f"{os.environ['GITHUB_SERVER_URL']}/{os.environ['GITHUB_REPOSITORY']}"
            f"/actions/runs/{os.environ['GITHUB_RUN_ID']}"
        ),
        "run_logs_url": (
            f"{os.environ['GITHUB_API_URL']}/repos/{os.environ['GITHUB_REPOSITORY']}"
            f"/actions/runs/{os.environ['GITHUB_RUN_ID']}/logs"
        ),
        "ref": os.environ["GITHUB_REF"],
        "sha": os.environ["GITHUB_SHA"],
        "repository_url": (
            f"{os.environ['GITHUB_SERVER_URL']}/{os.environ['GITHUB_REPOSITORY']}"
        ),
        "workflow_ref": os.environ["GITHUB_WORKFLOW_REF"],
        "workflow_sha": os.environ["GITHUB_WORKFLOW_SHA"],
    }
    if provenance["github_actions"] != expected_actions:
        fail(f"GitHub Actions provenance={provenance['github_actions']!r}")


def verify_logs(green_log: str, participant_log: str) -> None:
    green_lines = green_log.splitlines()
    if green_lines.count("INFO:adverify_judge:Loaded 20 campaigns and ground truth data") != 1:
        fail("green did not load exactly 20 campaigns once")
    if green_lines.count("INFO:adverify_judge:Evaluating 20 campaigns") != 1:
        fail("green did not evaluate exactly 20 campaigns once")

    pattern = re.compile(
        r"INFO:adverify_judge:Campaign (camp_\d{3}): "
        r"P=1\.00 R=1\.00 F1=1\.00"
    )
    logged_campaigns = [
        match.group(1)
        for line in green_lines
        if (match := pattern.fullmatch(line)) is not None
    ]
    if logged_campaigns != list(EXPECTED_TRUE_POSITIVES):
        fail(f"green campaign log order={logged_campaigns!r}")

    card_line = (
        "INFO:httpx:HTTP Request: GET "
        "http://anomaly_detector:9009/.well-known/agent-card.json "
        '"HTTP/1.1 200 OK"'
    )
    post_line = (
        "INFO:httpx:HTTP Request: POST http://anomaly_detector:9009/ "
        '"HTTP/1.1 200 OK"'
    )
    if green_lines.count(card_line) != 20:
        fail(f"green card GET count={green_lines.count(card_line)}")
    if green_lines.count(post_line) != 20:
        fail(f"green participant POST count={green_lines.count(post_line)}")

    combined = f"{green_log}\n{participant_log}"
    for marker in ("Traceback (most recent call last)", "ERROR:"):
        if marker in combined:
            fail(f"runtime logs contain {marker!r}")
    if "WARNING:adverify_judge" in green_log:
        fail("green log contains a judge warning")
    if "Uvicorn running on http://0.0.0.0:9009" not in participant_log:
        fail("participant did not report the leaderboard endpoint")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--provenance", type=Path, required=True)
    parser.add_argument("--green-log", type=Path, required=True)
    parser.add_argument("--participant-log", type=Path, required=True)
    args = parser.parse_args()

    participant_id = os.environ["ADVERIFY_AGENT_ID"]
    verify_results(load_json(args.results), participant_id)
    verify_provenance(load_json(args.provenance))
    verify_logs(
        args.green_log.read_text(encoding="utf-8"),
        args.participant_log.read_text(encoding="utf-8"),
    )
    print("Exact AdVerify result verified: 20/20 campaigns, P/R/F1 = 1.0")


if __name__ == "__main__":
    main()
