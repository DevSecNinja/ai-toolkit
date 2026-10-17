#!/usr/bin/env python3
"""Read-only discovery and explicitly approved, SHA-bound Renovate merges."""

import argparse
from datetime import date, datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import quote, urlsplit


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
DASHBOARD_INTRO = "This issue lists Renovate updates and detected dependencies."
DASHBOARD_SECTIONS = {
    "Abandoned Dependencies": "release_inactivity",
    "Deprecated Dependencies": "reported_deprecation",
    "Repository Problems": "warning",
    "Errored": "warning",
    "Pending Approval": "approval_wait",
    "Awaiting Schedule": "schedule",
    "Pending Status Checks": "pending",
    "Rate-Limited": "rate_limit",
    "Open": "open_updates",
    "Detected Dependencies": "inventory",
}

SNAPSHOT = """
query Snapshot($owner: String!, $name: String!, $number: Int!, $cursor: String) {
  repository(owner: $owner, name: $name) {
    nameWithOwner isArchived viewerPermission
    mergeCommitAllowed squashMergeAllowed rebaseMergeAllowed
    pullRequest(number: $number) {
      id number url title body state merged isDraft headRefOid baseRefOid baseRefName updatedAt
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
                  ... on CheckRun { name status conclusion detailsUrl startedAt completedAt }
                  ... on StatusContext { context state targetUrl createdAt }
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


def read_check_contexts(gh, repo, number, initial):
    pr = initial["pullRequest"]
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
    return contexts


def inspect_pr(gh, repo, number):
    initial = gh.snapshot(repo, number)
    pr = initial["pullRequest"]
    target_sha = base_target_sha(pr)
    contexts = read_check_contexts(gh, repo, number, initial)
    rules = gh.rules(repo, pr["baseRefName"])
    require(all(isinstance(rule, dict) and text(rule.get("type")) for rule in rules), "rules are unreadable")
    require(gh.snapshot(repo, number) == initial, "PR or CI changed during inspection; retriage")
    return {"repository": initial, "base_target_sha": target_sha, "checks": contexts, "rules": rules}


def issue_reference(value, repos):
    match = re.fullmatch(r"([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)#([1-9][0-9]*)", value)
    if not match:
        match = re.fullmatch(r"https://github\.com/([^/]+/[^/]+)/issues/([1-9][0-9]*)", value)
    require(match is not None, "issue must be owner/repo#number or a github.com issue URL")
    repo = repository(match[1])
    require(repo in repos, "dashboard issue is outside the explicit repository scope")
    return repo, int(match[2])


def timestamp(value):
    require(isinstance(value, str), "timestamp is missing")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise Refusal("timestamp is malformed") from exc
    require(parsed.tzinfo is not None, "timestamp has no timezone")
    return parsed


def abandoned_rows(body, today):
    rows, warnings, columns, fence = [], [], None, None
    for line in body.splitlines():
        delimiter = re.match(r"^\s*(`{3,}|~{3,})", line)
        if delimiter:
            token = delimiter[1]
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence):
                fence = None
            continue
        if fence is not None:
            continue
        if not line.strip().startswith("|"):
            continue
        cells = [cell.strip().strip("`") for cell in line.strip().strip("|").split("|")]
        if all(re.fullmatch(r":?-+:?", cell) for cell in cells):
            continue
        if "Datasource" in cells and "Package" in cells and "Last Updated" in cells:
            columns = cells
            continue
        if columns is None or len(cells) != len(columns):
            warnings.append("unrecognized abandoned-dependency table row: " + line)
            continue
        fields = dict(zip(columns, cells))
        package = re.fullmatch(r"\[([^\]]+)\]\((https://[^\s)]+)\)", fields["Package"])
        if not package or not text(fields["Datasource"]):
            warnings.append("unreadable abandoned-dependency identity: " + line)
            continue
        source = urlsplit(package[2])
        if not source.hostname or source.username or source.password:
            warnings.append("unreadable upstream link: " + line)
            continue
        last_updated = fields["Last Updated"]
        age = None
        try:
            require(re.fullmatch(r"\d{4}-\d{2}-\d{2}", last_updated), "unknown release date")
            released = date.fromisoformat(last_updated)
            require(released <= today, "reported release date is in the future")
            age = (today - released).days
        except (Refusal, ValueError) as exc:
            warnings.append(f"{package[1]}: {exc}; preserve the reported date without an age claim")
        rows.append({
            "datasource": fields["Datasource"], "dependency": package[1],
            "upstream_url": package[2], "reported_last_updated": last_updated,
            "reported_release_age_days": age, "evidence": line,
        })
    if not rows:
        warnings.append("no readable abandoned-dependency rows; inspect the original section")
    count = re.search(r"View abandoned dependencies \(([0-9]+)\)", body)
    if count and int(count[1]) != len(rows):
        warnings.append("abandoned-dependency count differs from parsed rows; inspect original section")
    return rows, warnings


def dashboard_sections(body, today):
    sections, current, fence = [], None, None
    for number, line in enumerate(body.splitlines(), 1):
        delimiter = re.match(r"^\s*(`{3,}|~{3,})", line)
        if delimiter:
            token = delimiter[1]
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence):
                fence = None
        heading = re.fullmatch(r"##[ \t]+(.+?)\s*", line) if fence is None else None
        if heading:
            current = {
                "title": heading[1], "kind": DASHBOARD_SECTIONS.get(heading[1], "unknown"),
                "line": number, "body": "", "entries": [], "dependencies": [], "warnings": [],
            }
            sections.append(current)
        elif current is not None:
            current["body"] += line + "\n"
            if fence is None and re.match(r"^\s*[-*] \[[ xX]\]", line):
                current["entries"].append({"evidence": line, "pr_references": []})
    for section in sections:
        if section["kind"] == "release_inactivity":
            section["dependencies"], section["warnings"] = abandoned_rows(section["body"], today)
        elif section["kind"] == "unknown":
            section["warnings"].append("unrecognized section; preserved for manual review")
    return sections


def dashboard_pr(gh, repo, number, observed):
    result = {"repo": repo, "number": number, "observed_at": observed.isoformat(), "errors": []}
    try:
        initial = gh.snapshot(repo, number)
        pr = initial["pullRequest"]
        require(pr["state"] in ("OPEN", "CLOSED", "MERGED"), "unreadable PR state")
        result.update(url=pr["url"], state=pr["state"], head_sha=pr["headRefOid"],
                      updated_at=pr.get("updatedAt"), ci={"state": "not_evaluated", "checks": []})
        if pr["state"] != "OPEN":
            return result
        checks = read_check_contexts(gh, repo, number, initial)
        require(gh.snapshot(repo, number) == initial, "PR or CI changed while correlating dashboard")
        states, details = [], []
        for check in checks:
            kind = check["__typename"]
            state = "unknown"
            if kind == "CheckRun":
                if check["status"] in ("QUEUED", "IN_PROGRESS", "WAITING", "REQUESTED", "PENDING"):
                    state = "pending"
                elif check["status"] == "COMPLETED":
                    state = {
                        "SUCCESS": "successful", "FAILURE": "failing", "TIMED_OUT": "failing",
                        "CANCELLED": "not_successful", "NEUTRAL": "not_successful", "SKIPPED": "not_successful",
                    }.get(check["conclusion"], "unknown")
            elif kind == "StatusContext":
                state = {"SUCCESS": "successful", "FAILURE": "failing", "ERROR": "failing",
                         "PENDING": "pending"}.get(check["state"], "unknown")
            details.append({"state": state, "evidence": check})
            states.append(state)
        summary = next((state for state in ("failing", "unknown", "pending", "not_successful")
                        if state in states), "successful" if states else "absent")
        if summary == "successful" and check_connection(pr)["state"] != "SUCCESS":
            summary = "unknown"
        if summary == "unknown":
            result["errors"].append("unknown or inconsistent CI state; inspect current checks")
        result["ci"] = {"state": summary, "rollup": check_connection(pr)["state"], "checks": details}
    except (Refusal, KeyError, TypeError, ValueError) as exc:
        result["errors"].append(str(exc))
        result["ci"] = {"state": "unknown", "checks": []}
        if "state" not in result:
            result["state"] = "missing_or_unreadable"
    return result


def read_dashboard(gh, repo, issue, allowed, observed, explicit, pr_cache):
    number = issue["number"]
    require(type(number) is int and number > 0, "invalid dashboard issue number")
    require("pull_request" not in issue, "explicit dashboard reference is a pull request")
    require(
        isinstance(issue.get("html_url"), str)
        and issue["html_url"].lower() == f"https://github.com/{repo}/issues/{number}",
        "out-of-scope or unreadable dashboard issue URL",
    )
    require(identity(issue["user"], allowed), "dashboard is not authored by a configured Renovate identity")
    require(text(issue["user"]["node_id"]), "dashboard author node ID is unreadable")
    body = issue["body"]
    require(isinstance(body, str), "dashboard body is unreadable")
    require(issue["state"] in ("open", "closed"), "dashboard state is unreadable")
    sections = dashboard_sections(body, observed.date())
    warnings = []
    if not body.startswith(DASHBOARD_INTRO):
        warnings.append("canonical dashboard introduction absent; explicit reference needs provenance/config verification")
    if not sections:
        warnings.append("no readable dashboard sections; inspect original issue/configuration")
    if issue["state"] != "open":
        warnings.append("dashboard issue is closed; do not treat it as a current backlog")
    try:
        require(timestamp(issue.get("updated_at")) <= observed, "dashboard updated_at is in the future")
    except Refusal as exc:
        warnings.append(str(exc))
    for section in sections:
        for entry in section["entries"]:
            for target in re.findall(r"\]\(([^)\s]+)\)", entry["evidence"]):
                match = re.fullmatch(r"\.\./pull/([1-9][0-9]*)(?:#[^\s]*)?", target)
                if not match:
                    match = re.fullmatch(rf"https://github\.com/{re.escape(repo)}/pull/([1-9][0-9]*)(?:#[^\s]*)?",
                                         target, re.IGNORECASE)
                if match:
                    pr_number = int(match[1])
                    key = (repo, pr_number)
                    if key not in pr_cache:
                        pr_cache[key] = dashboard_pr(gh, repo, pr_number, observed)
                    current = pr_cache[key]
                    entry["pr_references"].append({
                        "reference": target, "current": current,
                        "stale": current["state"] in ("CLOSED", "MERGED")
                        and section["kind"] in ("pending", "open_updates", "schedule", "approval_wait"),
                    })
                else:
                    entry["pr_references"].append({"reference": target, "status": "not_followed",
                                                   "reason": "not a same-repository github.com PR link"})
            if not entry["pr_references"]:
                entry["correlation"] = "no_pr_reference; branch markers are not proof that a PR or CI run exists"
    errors = [error for section in sections for entry in section["entries"]
              for ref in entry["pr_references"] for error in ref.get("current", {}).get("errors", [])]
    return {
        "repo": repo, "number": number, "url": issue["html_url"], "title": issue["title"],
        "state": issue["state"], "author": issue["user"], "updated_at": issue.get("updated_at"),
        "body_sha256": body_digest(body), "body": body,
        "identification": "explicit_reference_and_author" if explicit else "canonical_introduction_and_author",
        "sections": sections, "warnings": warnings, "errors": errors,
        "complete": not errors and not warnings and all(not section["warnings"] for section in sections),
    }


def dashboards(gh, repos, allowed, references, observed=None):
    observed = observed or datetime.now(timezone.utc)
    selected = [issue_reference(value, repos) for value in references]
    require(len(selected) == len(set(selected)), "duplicate dashboard issue references")
    reports, pr_cache = [], {}
    for repo in repos:
        report = {"repo": repo, "discovery": "none", "dashboards": [], "excluded": [], "errors": []}
        numbers = [number for scope, number in selected if scope == repo]
        try:
            if numbers:
                issues = ((number, gh.call(["--method", "GET", f"repos/{repo}/issues/{number}"]))
                          for number in numbers)
            else:
                issues = ((None, issue) for issue in gh.pages(f"repos/{repo}/issues?state=open"))
            seen = set()
            for requested, issue in issues:
                require(isinstance(issue, dict), "dashboard issue is unreadable")
                if not numbers and "pull_request" in issue:
                    continue
                number = issue["number"]
                require(type(number) is int and number > 0 and number not in seen, "invalid or duplicate issue during pagination")
                seen.add(number)
                if numbers:
                    require(number == requested, "explicit issue response has the wrong number")
                else:
                    if not identity(issue["user"], allowed):
                        continue
                    require(isinstance(issue["body"], str), "Renovate issue body is unreadable")
                    if not issue["body"].startswith(DASHBOARD_INTRO):
                        report["excluded"].append({"number": number, "reason": "no canonical dashboard introduction; specify an explicit issue if customized"})
                        continue
                report["dashboards"].append(read_dashboard(gh, repo, issue, allowed, observed, bool(numbers), pr_cache))
        except (Refusal, KeyError, TypeError, ValueError) as exc:
            report["errors"].append(str(exc))
        count = len(report["dashboards"])
        report["discovery"] = "multiple" if count > 1 else "single" if count else "unreadable" if report["errors"] else "none"
        report["complete"] = not report["errors"] and all(item["complete"] for item in report["dashboards"])
        reports.append(report)
    return {
        "version": 1, "host": HOST, "repositories": repos, "renovate_logins": allowed,
        "observed_at": observed.isoformat(), "reports": reports, "complete": all(item["complete"] for item in reports),
        "authorized": False,
    }


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
    dashboard = commands.add_parser("dashboards", help="read-only scoped Dependency Dashboard evidence and current PR state")
    dashboard.add_argument("--repo", action="append", required=True)
    dashboard.add_argument("--renovate-login", action="append")
    dashboard.add_argument("--issue", action="append", default=[], help="explicit scoped owner/repo#number or github.com issue URL")
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
        if args.command in ("discover", "dashboards"):
            repos = unique([repository(repo) for repo in args.repo], "repositories")
            allowed = logins(args.renovate_login or DEFAULT_LOGINS)
            result = dashboards(gh, repos, allowed, args.issue) if args.command == "dashboards" else discover(gh, repos, allowed)
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
