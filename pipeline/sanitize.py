"""Same-length replacements for stack hostnames, instance IDs, home paths, private IPs, and Jira identities (§6.3).

Replacements keep the original length so TUI boxes and columns in a cast stay aligned.
"""

import re


def _same_length(value: str, template: str) -> str:
    return (template * (len(value) // len(template) + 1))[: len(value)]


def find_replacements(text: str) -> dict[str, str]:
    reps: dict[str, str] = {}
    for host in set(re.findall(r"[a-z0-9-]+(?:\.[a-z0-9-]+)*\.splunkcloud\.com", text)):
        reps[host] = _same_length(host[: -len(".example.com")], "splunk-cloud-demo-stack-0001") + ".example.com"
    for stack in set(re.findall(r"fedsearch-demo-\d+", text)):
        reps[stack] = _same_length(stack, "acme-demo-stack1")
    for inst in set(re.findall(r"\b(?:sh|idx|c0m)-?i-[0-9a-f]{8,17}\b", text)):
        prefix = inst.split("-i-")[0]
        reps[inst] = f"{prefix}-i-" + "0" * (len(inst) - len(prefix) - 3)
    for home in set(re.findall(r"/Users/(?!Shared\b)[A-Za-z0-9._-]+", text)):
        reps[home] = "/Users/" + _same_length(home[len("/Users/"):], "demo")
    for ip in set(re.findall(r"\b(?:10|172|192)\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", text)):
        reps[ip] = re.sub(r"\d", "0", ip)
    for site in set(re.findall(r"[a-z0-9-]+\.atlassian\.net", text)):
        reps[site] = _same_length(site[: -len(".example.net")], "jirademosite") + ".example.net"
        # The site's bare name also appears on its own, such as the `name` in getAccessibleAtlassianResources.
        name = site.split(".")[0]
        if len(name) >= 5:
            reps[name] = _same_length(name, "jirademosite")
    for email in set(re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[a-z]{2,}", text)):
        if not re.search(r"@example\.(?:com|net|org)$", email):
            local = max(len(email) - len("@example.com"), 1)
            reps[email] = _same_length("x" * local, "analyst") + "@example.com"
    # Atlassian account IDs (new and legacy forms) and the site's cloudId.
    for account in set(re.findall(r"\b\d{6}:[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\b|\b[0-9a-f]{24}\b", text)):
        reps[account] = re.sub(r"[0-9a-f]", "0", account)
    for cloud in set(re.findall(r"cloudId\W{1,6}([0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12})", text)):
        reps[cloud] = re.sub(r"[0-9a-f]", "0", cloud)
    for name in set(re.findall(r'(?:\\?"displayName\\?": \\?")([^\\"]+)(?:\\?")', text)):
        if name not in {"Analyst", "admin"}:
            reps[name] = _same_length(name, "Analyst")
    return reps


def apply(text: str, reps: dict[str, str]) -> str:
    # Longest first, so a hostname is replaced before the stack name inside it.
    for old in sorted(reps, key=len, reverse=True):
        text = text.replace(old, reps[old])
    return text


LEFTOVER = re.compile(r"splunkcloud\.com|fedsearch|/Users/(?!Shared|demo)\w+|\b(?:sh|idx)-i-[1-9a-f]"
                      r"|\.atlassian\.net|@(?:gmail|splunk|cisco)\.com")


def leftovers(text: str) -> list[str]:
    return sorted(set(LEFTOVER.findall(text)))
