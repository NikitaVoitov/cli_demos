"""Same-length replacements for stack hostnames, instance IDs, home paths, and private IPs (§6.3).

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
    return reps


def apply(text: str, reps: dict[str, str]) -> str:
    # Longest first, so a hostname is replaced before the stack name inside it.
    for old in sorted(reps, key=len, reverse=True):
        text = text.replace(old, reps[old])
    return text


LEFTOVER = re.compile(r"splunkcloud\.com|fedsearch|/Users/(?!Shared|demo)\w+|\b(?:sh|idx)-i-[1-9a-f]")


def leftovers(text: str) -> list[str]:
    return sorted(set(LEFTOVER.findall(text)))
