#!/usr/bin/env python3
"""Read-only discovery and explicitly approved, SHA-bound Renovate merges."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import quote


HOST = "github.com"
PLAN_VERSION = 2
DEFAULT_LOGINS = ["renovate[bot]"]
DISABLED = (
    "\U0001f6a6 **Automerge**: Disabled by config. "
    "Please merge this manually once you are satisfied."
)
ENABLED = "\U0001f6a6 **Automerge**: Enabled."
EVIDENCE = ("changes", "upstream", "usage", "ci", "rules", "automerge", "breaking")
METHODS = {"merge": "MERGE", "squash": "SQUASH", "rebase": "REBASE"}

SNAPSHOT = """
query Snapshot($owner: String!, $name: String!, $number: Int!, $cursor: String) {
  repository(owner: $owner, name: $name) {
    nameWithOwner isArchived viewerPermission
    mergeCommitAllowed squashMergeAllowed rebaseMergeAllowed
    pullRequest(number: $number) {
      id number url title body state merged isDraft headRefOid baseRefOid baseRefName
      author { login __typename ... on Bot { id } ... on User { id } }
      autoMergeRequest { enabledAt }
      isMergeQueueEnabled isInMergeQueue mergeable mergeStateStatus reviewDecision
      baseRef {
        target { __typename oid }
        branchProtectionRule {
          requiresApprovingReviews requiredApprovingReviewCount
          requiredStatusCheckContexts
        }
      }
      commits(last: 1) {
        nodes {
          commit {
            oid
            statusCheckRollup {
              state
              contexts(first: 100, after: $cursor) {
                nodes {
                  __typename
                  ... on CheckRun { name status conclusion detailsUrl }
                  ... on StatusContext { context state targetUrl }
                }
                pageInfo { hasNextPage endCursor }
              }
            }
          }
        }
      }
    }
  }
}
"""
MERGE = """
mutation Merge($input: MergePullRequestInput!) {
  mergePullRequest(input: $input) { pullRequest { id state merged } }
}
"""
ENQUEUE = """
mutation Enqueue($input: EnqueuePullRequestInput!) {
  enqueuePullRequest(input: $input) { mergeQueueEntry { id } }
}
"""


class Refusal(Exception):
    """An invalid input, unreadable response, or eligibility blocker."""


def require(condition, message):
    if not condition:
        raise Refusal(message)


def text(value):
    return isinstance(value, str) and bool(value.strip())


def digest(data):
    return hashlib.sha256(data).hexdigest()


def body_digest(body):
    require(isinstance(body, str), "PR body is unreadable")
    return digest(body.encode("utf-8"))


def repository(value):
    require(
        isinstance(value, str)
        and re.fullmatch(r"[A-Za-z0-9-]+/[A-Za-z0-9_.-]+", value)
        and value.split("/")[1] not in (".", ".."),
        "repository must be an explicit owner/name on github.com",
    )
    return value.lower()


def unique(values, label):
    require(isinstance(values, list) and values, f"{label} must be a nonempty list")
    require(len(values) == len(set(values)), f"duplicate {label}")
    return values


def logins(values):
    unique(values, "Renovate logins")
    for value in values:
        require(
            isinstance(value, str)
            and re.fullmatch(r"[A-Za-z0-9-]+(?:\[bot\])?", value),
            "invalid Renovate login",
        )
    return [value.lower() for value in values]


def identity(author, allowed):
    require(isinstance(author, dict), "author is unreadable")
    kind = author.get("__typename", author.get("type"))
    login = author.get("login")
    require(text(login) and kind in ("Bot", "User"), "author identity is unreadable")
    login = login.lower()
    if kind == "Bot" and not login.endswith("[bot]"):
        login += "[bot]"
    # A User cannot impersonate the default Bot by matching a display name.
    require(not (kind == "User" and login.endswith("[bot]")), "invalid bot identity")
    return login in allowed


def classify(body, native_auto, queued=False):
    """Recognize only Renovate's canonical signal, never prose as approval."""
    if type(queued) is not bool:
        return "unknown", "merge queue membership is unreadable"
    if queued:
        return "enabled", "GitHub merge queue is active"
    if native_auto is not None:
        if isinstance(native_auto, dict) and (
            text(native_auto.get("enabledAt"))
            or (
                isinstance(native_auto.get("enabled_by"), dict)
                and text(native_auto["enabled_by"].get("login"))
            )
        ):
            return "enabled", "GitHub auto-merge is active"
        return "unknown", "GitHub auto-merge state is unreadable"
    if not isinstance(body, str):
        return "unknown", "PR body is unreadable"
    markers = []
    fence = None
    for line in body.splitlines():
        delimiter = re.match(r"^\s*(`{3,}|~{3,})", line)
        if delimiter:
            token = delimiter.group(1)
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence):
                fence = None
        if "**Automerge**:" in line:
            if fence is not None:
                return "unknown", "automerge marker occurs in a code example"
            markers.append(line.strip())
    if markers == [DISABLED]:
        return "manual", "canonical Renovate Disabled by config marker"
    if markers == [ENABLED]:
        return "enabled", "canonical Renovate Enabled marker"
    return "unknown", "missing, customized, duplicate, or conflicting automerge markers"


class GitHub:
    def graphql(self, query, variables):
        response = self.call(
            ["graphql", "--input", "-"], {"query": query, "variables": variables}
        )
        require(isinstance(response, dict), "GraphQL response is not an object")
        require(not response.get("errors"), f"GraphQL errors: {response.get('errors')}")
        require(isinstance(response.get("data"), dict), "GraphQL data is unreadable")
        return response["data"]

    def call(self, args, payload=None):
        env = os.environ.copy()
        env.update({"GH_PROMPT_DISABLED": "1", "GH_PAGER": "cat"})
        try:
            result = subprocess.run(
                ["gh", "api", "--hostname", HOST, *args],
                input=None if payload is None else json.dumps(payload),
                capture_output=True,
                text=True,
                timeout=90,
                check=False,
                env=env,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise Refusal(f"gh unavailable or timed out; do not retry a write: {exc}") from exc
        require(result.returncode == 0, f"gh failed: {result.stderr.strip()}")
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise Refusal("gh returned invalid JSON") from exc

    def pages(self, endpoint):
        page = 1
        separator = "&" if "?" in endpoint else "?"
        while True:
            rows = self.call(
                ["--method", "GET", f"{endpoint}{separator}per_page=100&page={page}"]
            )
            require(isinstance(rows, list), "REST page is not a list")
            yield from rows
            if len(rows) < 100:
                break
            page += 1

    def snapshot(self, repo, number, cursor=None):
        owner, name = repo.split("/")
        data = self.graphql(
            SNAPSHOT, {"owner": owner, "name": name, "number": number, "cursor": cursor}
        )
        result = data.get("repository")
        require(isinstance(result, dict), f"repository {repo} is unreadable")
        require(repository(result["nameWithOwner"]) == repo, "repository scope changed")
        pr = result.get("pullRequest")
        require(isinstance(pr, dict) and pr.get("number") == number, "PR is unreadable")
        return result

    def rules(self, repo, base):
        return list(self.pages(f"repos/{repo}/rules/branches/{quote(base, safe='')}"))

    def write(self, pr, action):
        payload = {"pullRequestId": pr["id"], "expectedHeadOid": pr["headRefOid"]}
        if action == "queue":
            payload["jump"] = False
            return self.graphql(ENQUEUE, {"input": payload})
        payload["mergeMethod"] = METHODS[action]
        return self.graphql(MERGE, {"input": payload})


def discover(gh, repos, allowed):
    candidates, excluded, errors = [], [], []
    for repo in repos:
        try:
            seen = set()
            for pr in gh.pages(f"repos/{repo}/pulls?state=open"):
                require(repository(pr["base"]["repo"]["full_name"]) == repo, "out-of-scope PR")
                number = pr["number"]
                require(type(number) is int and number > 0, "invalid PR number")
                require(number not in seen, "discovery changed during pagination; rerun")
                seen.add(number)
                require(pr["state"] == "open", "discovery returned a non-open PR")
                if not identity(pr["user"], allowed):
                    excluded.append({"repo": repo, "number": number, "reason": "not a configured Renovate identity"})
                    continue
                require("auto_merge" in pr, "native auto-merge state is unreadable")
                status, reason = classify(pr["body"], pr["auto_merge"])
                candidates.append({
                    "repo": repo,
                    "number": number,
                    "head_sha": pr["head"]["sha"],
                    "author_id": pr["user"]["node_id"],
                    "classification": status,
                    "classification_reason": reason,
                    "title": pr["title"],
                    "url": pr["html_url"],
                })
        except (Refusal, KeyError, TypeError) as exc:
            errors.append({"repo": repo, "error": str(exc)})
    return {
        "version": 1, "host": HOST, "repositories": repos,
        "renovate_logins": allowed, "candidates": candidates,
        "excluded": excluded, "errors": errors, "complete": not errors,
    }


def check_connection(pr):
    nodes = pr["commits"]["nodes"]
    require(len(nodes) == 1, "latest commit is absent")
    commit = nodes[0]["commit"]
    require(commit["oid"] == pr["headRefOid"], "checks are not for the current head")
    rollup = commit["statusCheckRollup"]
    require(isinstance(rollup, dict), "checks are absent or unreadable")
    return rollup


def base_target_sha(pr):
    ref = pr.get("baseRef")
    require(isinstance(ref, dict), "current base ref is absent or unreadable; retriage")
    target = ref.get("target")
    require(
        isinstance(target, dict) and target.get("__typename") == "Commit"
        and isinstance(target.get("oid"), str)
        and re.fullmatch(r"[0-9a-f]{40}", target["oid"]),
        "current base target commit is absent or unreadable; retriage",
    )
    return target["oid"]


def inspect_pr(gh, repo, number):
    initial = gh.snapshot(repo, number)
    pr = initial["pullRequest"]
    target_sha = base_target_sha(pr)
    stable = {key: value for key, value in pr.items() if key != "commits"}
    rollup = check_connection(pr)
    contexts, cursors = [], set()
    while True:
        connection = rollup["contexts"]
        require(isinstance(connection["nodes"], list), "check contexts are unreadable")
        contexts.extend(connection["nodes"])
        page = connection["pageInfo"]
        require(type(page["hasNextPage"]) is bool, "check pagination is unreadable")
        if not page["hasNextPage"]:
            break
        cursor = page["endCursor"]
        require(text(cursor) and cursor not in cursors, "invalid check pagination cursor")
        cursors.add(cursor)
        next_pr = gh.snapshot(repo, number, cursor)["pullRequest"]
        require(
            {key: value for key, value in next_pr.items() if key != "commits"} == stable,
            "PR changed while reading checks; retriage",
        )
        rollup = check_connection(next_pr)
        require(rollup["state"] == check_connection(pr)["state"], "CI changed during pagination")
    rules = gh.rules(repo, pr["baseRefName"])
    require(all(isinstance(rule, dict) and text(rule.get("type")) for rule in rules), "rules are unreadable")
    require(gh.snapshot(repo, number) == initial, "PR or CI changed during inspection; retriage")
    return {"repository": initial, "base_target_sha": target_sha, "checks": contexts, "rules": rules}


def eligibility(snapshot, candidate, allowed):
    repo = snapshot["repository"]
    pr = repo["pullRequest"]
    require(pr["state"] == "OPEN" and pr["merged"] is False, "PR is closed or already merged")
    require(pr["isDraft"] is False, "PR is a draft")
    require(repo["isArchived"] is False, "repository is archived")
    require(repo["viewerPermission"] in ("WRITE", "MAINTAIN", "ADMIN"), "no repository write permission")
    require(identity(pr["author"], allowed), "not a configured Renovate identity")
    require(pr["author"]["id"] == candidate["author_id"], "author identity changed")
    require(pr["headRefOid"] == candidate["head_sha"], "head changed; retriage and reconfirm")
    require(pr["baseRefName"] == candidate["base_ref"], "base branch changed; retriage")
    require(pr["baseRefOid"] == candidate["base_sha"], "recorded PR base changed; retriage and reconfirm")
    require(base_target_sha(pr) == candidate["base_target_sha"], "current base advanced; retriage and reconfirm")
    require(body_digest(pr["body"]) == candidate["body_sha256"], "PR body changed; retriage")
    manual, reason = classify(pr["body"], pr["autoMergeRequest"], pr["isInMergeQueue"])
    require(manual == "manual", f"not manual-only: {reason}")
    require(pr["mergeable"] == "MERGEABLE", "PR is conflicted or mergeability is unknown")
    require(pr["mergeStateStatus"] == "CLEAN", f"repository requirements not clean: {pr['mergeStateStatus']}")
    require(pr["reviewDecision"] in (None, "APPROVED"), "reviews are pending or changes requested")
    require(pr["baseRef"] is not None, "base ref or branch protection is unreadable")
    protection = pr["baseRef"]["branchProtectionRule"]
    required_names = set()
    review_required = False
    if protection is not None:
        review_required = protection["requiresApprovingReviews"] or protection["requiredApprovingReviewCount"] > 0
        required_names.update(protection["requiredStatusCheckContexts"])
    for rule in snapshot["rules"]:
        if rule["type"] == "pull_request":
            review_required = review_required or rule["parameters"]["required_approving_review_count"] > 0
            methods = rule["parameters"].get("allowed_merge_methods")
            if methods is not None and candidate["action"] != "queue":
                require(candidate["action"] in methods, "merge method forbidden by branch rules")
        if rule["type"] == "required_status_checks":
            required_names.update(item["context"] for item in rule["parameters"]["required_status_checks"])
    if review_required:
        require(pr["reviewDecision"] == "APPROVED", "required reviews are not approved")
    checks = snapshot["checks"]
    require(checks, "checks are absent")
    require(check_connection(pr)["state"] == "SUCCESS", "CI rollup is not successful")
    names = set()
    for check in checks:
        if check["__typename"] == "CheckRun":
            names.add(check["name"])
            require(check["status"] == "COMPLETED" and check["conclusion"] == "SUCCESS", "a check is not successful")
        elif check["__typename"] == "StatusContext":
            names.add(check["context"])
            require(check["state"] == "SUCCESS", "a commit status is not successful")
        else:
            raise Refusal("unknown check type")
    require(required_names <= names, "required checks are missing")
    queue = pr["isMergeQueueEnabled"]
    require(type(queue) is bool, "merge queue policy is unreadable")
    require((candidate["action"] == "queue") == queue, "queue policy changed or action mismatches policy")
    if not queue:
        field = {"merge": "mergeCommitAllowed", "squash": "squashMergeAllowed", "rebase": "rebaseMergeAllowed"}[candidate["action"]]
        require(repo[field] is True, "repository disallows the selected merge method")


def strict_object(value, keys, label):
    require(isinstance(value, dict) and set(value) == set(keys), f"invalid {label} fields")


def sha(value, length=40):
    require(isinstance(value, str) and re.fullmatch(rf"[0-9a-f]{{{length}}}", value), "invalid SHA")


def plan_data(plan):
    strict_object(plan, ("version", "host", "repositories", "renovate_logins", "candidates"), "plan")
    require(
        type(plan["version"]) is int and plan["version"] == PLAN_VERSION and plan["host"] == HOST,
        "unsupported plan version or host; retriage with a version 2 plan and reconfirm",
    )
    repos = unique([repository(repo) for repo in plan["repositories"]], "repositories")
    require(repos == plan["repositories"], "plan repositories must be lowercase")
    allowed = logins(plan["renovate_logins"])
    require(isinstance(plan["candidates"], list), "candidates must be a list")
    index = {}
    for candidate in plan["candidates"]:
        strict_object(candidate, (
            "repo", "number", "head_sha", "base_ref", "base_sha", "base_target_sha", "author_id", "body_sha256",
            "recommendation", "reasons", "confidence", "evidence", "action",
        ), "candidate")
        require(candidate["repo"] in repos, "candidate outside repository scope")
        require(type(candidate["number"]) is int and candidate["number"] > 0, "invalid PR number")
        key = f"{candidate['repo']}#{candidate['number']}"
        require(key not in index, "duplicate candidate")
        sha(candidate["head_sha"])
        sha(candidate["base_sha"])
        sha(candidate["base_target_sha"])
        sha(candidate["body_sha256"], 64)
        require(text(candidate["base_ref"]) and text(candidate["author_id"]), "missing base or author")
        require(candidate["recommendation"] in ("merge", "hold"), "invalid recommendation")
        require(candidate["confidence"] in ("high", "medium", "low"), "invalid confidence")
        require(candidate["action"] in (*METHODS, "queue"), "invalid action")
        require(isinstance(candidate["reasons"], list) and candidate["reasons"] and all(text(item) for item in candidate["reasons"]), "reasons are required")
        strict_object(candidate["evidence"], EVIDENCE, "evidence")
        for category in EVIDENCE:
            items = candidate["evidence"][category]
            require(isinstance(items, list) and items, f"{category} evidence is required")
            for item in items:
                strict_object(item, ("source", "summary"), "evidence item")
                require(text(item["source"]) and text(item["summary"]), "evidence source and summary are required")
        index[key] = candidate
    return index, allowed


def approval_data(approval, plan_bytes, index, selected):
    strict_object(approval, ("version", "plan_sha256", "user_confirmation", "selected"), "approval")
    require(
        type(approval["version"]) is int and approval["version"] == PLAN_VERSION,
        "unsupported approval version; retriage and reconfirm the version 2 plan",
    )
    require(approval["plan_sha256"] == digest(plan_bytes), "plan changed since confirmation")
    require(text(approval["user_confirmation"]), "explicit user confirmation is required")
    unique(selected, "selected PRs")
    require(isinstance(approval["selected"], list) and approval["selected"], "approval selection is empty")
    approved = []
    for item in approval["selected"]:
        strict_object(item, ("repo", "number", "head_sha", "action"), "approved selection")
        require(type(item["number"]) is int and item["number"] > 0, "invalid approved PR number")
        key = f"{item['repo']}#{item['number']}"
        require(key in index, "approved PR is absent from the reviewed plan")
        candidate = index[key]
        require(all(item[field] == candidate[field] for field in item), "approved SHA or action differs from review")
        require(candidate["recommendation"] == "merge" and candidate["confidence"] == "high", "only high-confidence merge recommendations can execute")
        approved.append(key)
    unique(approved, "approved PRs")
    require(approved == selected, "CLI selection must exactly match approved set and order")
    return [index[key] for key in selected]


def execute(gh, candidates, allowed):
    results, stopped = [], False
    for candidate in candidates:
        result = {key: candidate[key] for key in ("repo", "number", "head_sha", "action")}
        if stopped:
            result.update(status="skipped", reason="previous write failed or queued; inspect outcomes before continuing")
            results.append(result)
            continue
        try:
            snapshot = inspect_pr(gh, candidate["repo"], candidate["number"])
            eligibility(snapshot, candidate, allowed)
        except (Refusal, KeyError, TypeError, ValueError) as exc:
            result.update(status="blocked", reason=str(exc))
            results.append(result)
            continue
        pr = snapshot["repository"]["pullRequest"]
        error = None
        try:
            gh.write(pr, candidate["action"])
        except (Refusal, KeyError, TypeError) as exc:
            error = str(exc)
        try:
            current = gh.snapshot(candidate["repo"], candidate["number"])["pullRequest"]
            require(current["headRefOid"] == candidate["head_sha"], "head changed during write; outcome requires inspection")
            if current["merged"] is True and current["state"] == "MERGED":
                result.update(status="merged", reason="GitHub confirms merged")
            elif current["isInMergeQueue"] is True and current["state"] == "OPEN":
                result.update(status="queued", reason="GitHub confirms queued, NOT merged")
                stopped = True
            else:
                raise Refusal("write not confirmed as merged or queued; inspect before any retry")
            if error:
                result["warning"] = error
        except (Refusal, KeyError, TypeError) as exc:
            result.update(status="failed", reason=f"{error + '; ' if error else ''}{exc}")
            stopped = True
        results.append(result)
    return results


def load_json(path):
    data = Path(path).read_bytes()
    return data, json.loads(data)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    discovery = commands.add_parser("discover", help="read-only, explicitly scoped discovery")
    discovery.add_argument("--repo", action="append", required=True)
    discovery.add_argument("--renovate-login", action="append")
    inspect = commands.add_parser("inspect", help="read-only current CI, rules and PR evidence")
    inspect.add_argument("--repo", required=True)
    inspect.add_argument("--number", type=int, required=True)
    validate = commands.add_parser("validate-plan", help="offline handoff validation and digest; NOT approval")
    validate.add_argument("--plan", required=True)
    merge = commands.add_parser("merge", help="execute ONLY an explicitly confirmed plan selection")
    merge.add_argument("--plan", required=True)
    merge.add_argument("--approval", required=True)
    merge.add_argument("--select", action="append", required=True)
    args = parser.parse_args(argv)
    try:
        gh = GitHub()
        if args.command == "discover":
            repos = unique([repository(repo) for repo in args.repo], "repositories")
            result = discover(gh, repos, logins(args.renovate_login or DEFAULT_LOGINS))
            code = 0 if result["complete"] else 1
        elif args.command == "inspect":
            require(args.number > 0, "PR number must be positive")
            result = inspect_pr(gh, repository(args.repo), args.number)
            pr = result["repository"]["pullRequest"]
            result["body_sha256"] = body_digest(pr["body"])
            result["classification"], result["classification_reason"] = classify(
                pr["body"], pr["autoMergeRequest"], pr["isInMergeQueue"]
            )
            code = 0
        else:
            plan_bytes, plan = load_json(args.plan)
            index, allowed = plan_data(plan)
            if args.command == "validate-plan":
                result = {"plan_sha256": digest(plan_bytes), "candidates": list(index), "authorized": False}
                code = 0
            else:
                _, approval = load_json(args.approval)
                candidates = approval_data(approval, plan_bytes, index, args.select)
                result = {"results": execute(gh, candidates, allowed)}
                code = 0 if all(item["status"] == "merged" for item in result["results"]) else 1
        print(json.dumps(result, indent=2))
        return code
    except (Refusal, OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
