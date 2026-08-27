#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""sillybench harness — run one experiment against one homelab model.

Sends the experiment's prompt.md to the LiteLLM proxy as a single user
message, with client-side tools enabled (web_fetch, web_search) so the
model can read real websites and check facts. Streams the response,
executes tool calls in a loop, extracts the final artifact (html/svg),
and writes it to <experiment>/<model>.<ext>.

Usage:
    uv run harness/run.py <experiment> <model> [options]

Example:
    uv run harness/run.py peregian-digital-hub glm-5.3-flash \
        --temperature 1.0 --top-p 0.95 --max-tokens 60000
"""

import argparse
import html as htmllib
import http.client
import io
import json
import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEFAULT_BASE_URL = "http://100.101.13.98:4000"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_fetch",
            "description": (
                "Fetch a URL and return its readable text content plus the links found "
                "on the page. Use it to read real websites so your output is grounded "
                "in facts instead of invented."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Full URL to fetch, including scheme"},
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": (
                "Search the web (DuckDuckGo) and return result titles, URLs and snippets. "
                "Use it to find pages or to check facts you are unsure about."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                },
                "required": ["query"],
            },
        },
    },
]


# ---------------------------------------------------------------- tools

def html_to_text(page: str) -> str:
    page = re.sub(r"<(script|style|noscript|svg)[^>]*>.*?</\1>", " ", page, flags=re.S | re.I)
    page = re.sub(r"<!--.*?-->", " ", page, flags=re.S)
    # keep a hint of structure
    page = re.sub(r"</(p|div|li|h[1-6]|tr|section|article|br)>", "\n", page, flags=re.I)
    page = re.sub(r"<[^>]+>", " ", page)
    page = htmllib.unescape(page)
    page = re.sub(r"[ \t]+", " ", page)
    page = re.sub(r"\n\s*\n+", "\n", page)
    return page.strip()


def extract_links(page: str, base_url: str, cap: int = 60) -> list[str]:
    seen, links = set(), []
    host = urllib.parse.urlparse(base_url).netloc
    hrefs = re.findall(r'<a[^>]+href=["\']([^"\'#]+)["\']', page, flags=re.I)
    # same-site links first, then external
    for external in (False, True):
        for href in hrefs:
            url = urllib.parse.urljoin(base_url, href.strip())
            if not url.startswith(("http://", "https://")):
                continue
            is_external = urllib.parse.urlparse(url).netloc != host
            if is_external != external or url in seen:
                continue
            seen.add(url)
            links.append(url)
            if len(links) >= cap:
                return links
    return links


def tool_web_fetch(url: str, max_chars: int = 20000) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read(800_000)
            final_url = resp.geturl()
            ctype = resp.headers.get("Content-Type", "")
    except (urllib.error.URLError, socket.timeout, ValueError) as e:
        return f"ERROR fetching {url}: {e}"
    charset = "utf-8"
    m = re.search(r"charset=([\w-]+)", ctype)
    if m:
        charset = m.group(1)
    body = raw.decode(charset, errors="replace")
    if "html" not in ctype.lower() and not body.lstrip()[:200].lower().startswith(("<!doctype", "<html")):
        text = body[:max_chars]
        return f"URL: {final_url}\nContent-Type: {ctype}\n\n{text}"
    text = html_to_text(body)
    links = extract_links(body, final_url)
    out = f"URL: {final_url}\n\n{text[:max_chars]}"
    if len(text) > max_chars:
        out += "\n[...truncated]"
    if links:
        out += "\n\nLINKS ON PAGE:\n" + "\n".join(links)
    return out


def tool_web_search(query: str, max_results: int = 8) -> str:
    url = "https://html.duckduckgo.com/html/?" + urllib.parse.urlencode({"q": query})
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            page = resp.read(800_000).decode("utf-8", errors="replace")
    except (urllib.error.URLError, socket.timeout) as e:
        return f"ERROR searching for {query!r}: {e}"
    results = []
    for m in re.finditer(
        r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>.*?'
        r'(?:<a[^>]+class="result__snippet"[^>]*>(.*?)</a>)?(?=<div[^>]+class="result|$)',
        page,
        flags=re.S,
    ):
        href, title, snippet = m.groups()
        # ddg wraps targets in a redirect: //duckduckgo.com/l/?uddg=<real url>
        q = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
        real = q.get("uddg", [href])[0]
        title = html_to_text(title)
        snippet = html_to_text(snippet or "")
        results.append(f"{title}\n{real}\n{snippet}")
        if len(results) >= max_results:
            break
    return "\n\n".join(results) if results else f"No results for {query!r}"


def run_tool(name: str, args: dict) -> str:
    if name == "web_fetch":
        return tool_web_fetch(str(args.get("url", "")))
    if name == "web_search":
        return tool_web_search(str(args.get("query", "")))
    return f"ERROR: unknown tool {name!r}"


# ---------------------------------------------------------------- model I/O

def get_api_key() -> str:
    out = subprocess.run(
        ["jq", "-r", ".provider.homelab.options.apiKey",
         str(Path.home() / ".config/opencode/opencode.json")],
        capture_output=True, text=True,
    )
    key = out.stdout.strip()
    if not key or key == "null":
        sys.exit("could not read homelab api key from ~/.config/opencode/opencode.json")
    return key


def stream_round(base_url: str, key: str, payload: dict, log: io.TextIOBase,
                 attempts: int = 4):
    """POST one streaming round, retrying on dead/silent connections."""
    for attempt in range(1, attempts + 1):
        try:
            return _stream_once(base_url, key, payload, log)
        except (TimeoutError, socket.timeout, urllib.error.URLError,
                ConnectionError, http.client.HTTPException) as e:
            if attempt == attempts:
                raise
            print(f"  ! stream attempt {attempt} failed ({e!r}); retrying in 30s",
                  flush=True)
            time.sleep(30)


def _stream_once(base_url: str, key: str, payload: dict, log: io.TextIOBase):
    req = urllib.request.Request(
        base_url.rstrip("/") + "/v1/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    content, reasoning, finish, usage = "", "", None, None
    tool_calls: dict[int, dict] = {}
    last_report = time.time()
    with urllib.request.urlopen(req, timeout=900) as resp:
        for raw_line in resp:
            line = raw_line.decode("utf-8", errors="replace")
            log.write(line)
            if not line.startswith("data: "):
                continue
            data = line[6:].strip()
            if data == "[DONE]":
                break
            try:
                chunk = json.loads(data)
            except json.JSONDecodeError:
                continue
            if chunk.get("usage"):
                usage = chunk["usage"]
            for ch in chunk.get("choices", []):
                delta = ch.get("delta") or {}
                if delta.get("content"):
                    content += delta["content"]
                if delta.get("reasoning_content"):
                    reasoning += delta["reasoning_content"]
                for tc in delta.get("tool_calls") or []:
                    slot = tool_calls.setdefault(
                        tc.get("index", 0),
                        {"id": None, "type": "function", "function": {"name": "", "arguments": ""}},
                    )
                    if tc.get("id"):
                        slot["id"] = tc["id"]
                    fn = tc.get("function") or {}
                    if fn.get("name"):
                        slot["function"]["name"] += fn["name"]
                    if fn.get("arguments"):
                        slot["function"]["arguments"] += fn["arguments"]
                if ch.get("finish_reason"):
                    finish = ch["finish_reason"]
            if time.time() - last_report > 30:
                print(f"  … reasoning {len(reasoning)} chars, content {len(content)} chars",
                      flush=True)
                last_report = time.time()
    calls = [tool_calls[i] for i in sorted(tool_calls)]
    return content, reasoning, calls, finish, usage


def looks_like_artifact(text: str, kind: str) -> bool:
    if kind == "svg":
        return "<svg" in text
    if kind == "html":
        return bool(re.search(r"<!doctype|<html", text, re.I))
    return len(text.strip()) > 0


def extract_artifact(text: str, kind: str) -> str:
    t = text.strip()
    m = re.search(r"```(?:svg|html|xml)?\s*\n(.*?)```", t, re.S)
    if m:
        t = m.group(1)
    if kind == "svg":
        i, j = t.find("<svg"), t.rfind("</svg>")
        if i != -1 and j != -1:
            t = t[i:j + len("</svg>")]
    elif kind == "html":
        starts = [x for x in (t.find("<!DOCTYPE"), t.find("<!doctype"), t.find("<html")) if x != -1]
        j = t.rfind("</html>")
        if starts and j != -1:
            t = t[min(starts):j + len("</html>")]
    return t.strip() + "\n"


# ---------------------------------------------------------------- main

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("experiment", help="experiment folder name, e.g. peregian-digital-hub")
    ap.add_argument("model", help="LiteLLM model name, e.g. glm-5.3-flash")
    ap.add_argument("--max-tokens", type=int, default=60000)
    ap.add_argument("--temperature", type=float, default=None)
    ap.add_argument("--top-p", type=float, default=None)
    ap.add_argument("--kind", choices=["html", "svg", "text"], default=None,
                    help="artifact type; default: inferred from prompt.md")
    ap.add_argument("--no-tools", action="store_true", help="disable web_fetch/web_search")
    ap.add_argument("--max-rounds", type=int, default=24,
                    help="max model turns (tool rounds + final answer)")
    ap.add_argument("--base-url", default=DEFAULT_BASE_URL)
    ap.add_argument("--out", default=None, help="override output path")
    args = ap.parse_args()

    exp_dir = REPO / args.experiment
    prompt_file = exp_dir / "prompt.md"
    if not prompt_file.is_file():
        sys.exit(f"no prompt.md in {exp_dir}")
    prompt = prompt_file.read_text()

    kind = args.kind
    if kind is None:
        kind = "svg" if re.search(r"\bsvg\b", prompt, re.I) else \
               "html" if re.search(r"\bhtml\b", prompt, re.I) else "text"
    ext = {"html": "html", "svg": "svg", "text": "md"}[kind]
    out_path = Path(args.out) if args.out else exp_dir / f"{args.model}.{ext}"

    key = get_api_key()
    logs = REPO / "harness" / "logs"
    logs.mkdir(exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    run_name = f"{exp_dir.name}-{args.model}-{stamp}"
    sse_log = open(logs / f"{run_name}.sse", "w", buffering=1)
    transcript_path = logs / f"{run_name}.json"

    messages = [{"role": "user", "content": prompt}]
    payload_base = {
        "model": args.model,
        "max_tokens": args.max_tokens,
        "stream": True,
        "stream_options": {"include_usage": True},
    }
    if args.temperature is not None:
        payload_base["temperature"] = args.temperature
    if args.top_p is not None:
        payload_base["top_p"] = args.top_p
    if not args.no_tools:
        payload_base["tools"] = TOOLS

    print(f"experiment={args.experiment} model={args.model} kind={kind} "
          f"tools={'off' if args.no_tools else 'web_fetch+web_search'}", flush=True)

    final_content, total_usage, nudges = "", [], 0
    t0 = time.time()
    for rnd in range(1, args.max_rounds + 1):
        print(f"[round {rnd}] requesting…", flush=True)
        content, reasoning, calls, finish, usage = stream_round(
            args.base_url, key, {**payload_base, "messages": messages}, sse_log)
        if usage:
            total_usage.append(usage)
        print(f"[round {rnd}] finish={finish} reasoning={len(reasoning)}ch "
              f"content={len(content)}ch tool_calls={len(calls)}", flush=True)
        if finish == "tool_calls" and calls:
            messages.append({"role": "assistant", "content": content or None,
                             "tool_calls": calls})
            for call in calls:
                name = call["function"]["name"]
                try:
                    fn_args = json.loads(call["function"]["arguments"] or "{}")
                except json.JSONDecodeError:
                    fn_args = {}
                target = fn_args.get("url") or fn_args.get("query") or ""
                print(f"  -> {name}({target})", flush=True)
                result = run_tool(name, fn_args)
                messages.append({"role": "tool", "tool_call_id": call["id"],
                                 "content": result})
            continue
        messages.append({"role": "assistant", "content": content})
        if finish == "length":
            print("WARNING: hit max_tokens — output is truncated", flush=True)
        elif not looks_like_artifact(content, kind) and nudges < 2:
            # model announced the artifact but stopped without emitting it
            nudges += 1
            print(f"[nudge {nudges}] final message contained no {kind} — asking again",
                  flush=True)
            messages.append({"role": "user",
                             "content": f"Now reply with the complete {kind}. "
                                        f"Output only the {kind}, nothing else."})
            continue
        final_content = content
        break
    else:
        print(f"WARNING: still calling tools after {args.max_rounds} rounds; stopping",
              flush=True)

    sse_log.close()
    transcript_path.write_text(json.dumps(
        {"experiment": args.experiment, "model": args.model, "kind": kind,
         "elapsed_s": round(time.time() - t0), "usage": total_usage,
         "messages": messages}, indent=2))

    if not looks_like_artifact(final_content, kind):
        sys.exit(f"no {kind} artifact produced — leaving any existing output "
                 f"untouched; see {transcript_path}")

    artifact = extract_artifact(final_content, kind)
    out_path.write_text(artifact)
    mins = (time.time() - t0) / 60
    comp = sum(u.get("completion_tokens", 0) for u in total_usage)
    print(f"\nwrote {out_path} ({len(artifact)} chars) in {mins:.1f} min, "
          f"{comp} completion tokens across {len(total_usage)} round(s)", flush=True)
    print(f"transcript: {transcript_path}", flush=True)


if __name__ == "__main__":
    main()
