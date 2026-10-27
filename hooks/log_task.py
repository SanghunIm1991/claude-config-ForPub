"""SessionEnd hook: 開発依頼ログをJSONLに1行追記する。

目的: Claude Codeへの依頼ごとに「依頼要約/成果物要約/モデル/effort/所要時間/トークン数」
だけを ~/.claude/dev-task-log.jsonl に蓄積し、将来の見積もり精度向上に使う。

安全策:
- どの例外も session end 自体をブロックしないよう握りつぶし、デバッグログにのみ残す。
- 要約生成のため内部的に `claude -p` を再帰呼び出しするが、環境変数 CLAUDE_TASKLOG_INTERNAL=1
  を子プロセスに継承させることで、子セッションの SessionEnd で再度このスクリプトが
  起動しても即座に return し、無限再帰を防ぐ。
"""
import sys
import os
import re
import json
import subprocess
import datetime
import traceback

HOME = os.path.expanduser("~")
LOG_PATH = os.path.join(HOME, ".claude", "dev-task-log.jsonl")
DEBUG_LOG_PATH = os.path.join(HOME, ".claude", "dev-task-log.errors.log")
GUARD_ENV = "CLAUDE_TASKLOG_INTERNAL"
MIN_ASSISTANT_TURNS = 2
SUMMARY_INPUT_CHAR_LIMIT = 1500
SUMMARY_OUTPUT_CHAR_LIMIT = 80


def main():
    if os.environ.get(GUARD_ENV) == "1":
        return
    try:
        hook_input = json.load(sys.stdin)
    except Exception:
        return

    transcript_path = hook_input.get("transcript_path")
    session_id = hook_input.get("session_id")
    cwd = hook_input.get("cwd")
    if not transcript_path or not os.path.exists(transcript_path):
        return

    try:
        process_session(transcript_path, session_id, cwd)
    except Exception:
        _log_error(traceback.format_exc())


def _log_error(text):
    try:
        with open(DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(datetime.datetime.now().isoformat() + "\n")
            f.write(text)
            f.write("\n")
    except Exception:
        pass


def parse_transcript(transcript_path):
    """トランスクリプトJSONLを1回走査し、集計に必要な値を抽出する。"""
    first_user_text = None
    last_assistant_text = None
    first_ts = None
    last_ts = None
    effort_values = []
    usage_by_model = {}
    assistant_turns = 0

    with open(transcript_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except Exception:
                continue

            ts = d.get("timestamp")
            if ts:
                if first_ts is None:
                    first_ts = ts
                last_ts = ts

            t = d.get("type")
            if t == "user":
                origin = d.get("origin") or {}
                content = d.get("message", {}).get("content")
                if (
                    origin.get("kind") == "human"
                    and isinstance(content, str)
                    and first_user_text is None
                ):
                    first_user_text = content

            elif t == "assistant":
                assistant_turns += 1
                is_sidechain = bool(d.get("isSidechain"))
                msg = d.get("message", {})
                model = msg.get("model")
                usage = msg.get("usage") or {}
                effort = d.get("effort")
                if effort and not is_sidechain:
                    effort_values.append(effort)
                if model:
                    agg = usage_by_model.setdefault(
                        model,
                        {
                            "input_tokens": 0,
                            "output_tokens": 0,
                            "cache_read_tokens": 0,
                            "cache_creation_tokens": 0,
                        },
                    )
                    agg["input_tokens"] += usage.get("input_tokens", 0) or 0
                    agg["output_tokens"] += usage.get("output_tokens", 0) or 0
                    agg["cache_read_tokens"] += (
                        usage.get("cache_read_input_tokens", 0) or 0
                    )
                    agg["cache_creation_tokens"] += (
                        usage.get("cache_creation_input_tokens", 0) or 0
                    )

                content = msg.get("content")
                if not is_sidechain and isinstance(content, list):
                    texts = [
                        c.get("text", "")
                        for c in content
                        if isinstance(c, dict) and c.get("type") == "text"
                    ]
                    if texts and texts[0].strip():
                        last_assistant_text = texts[0]

    wall_sec = None
    if first_ts and last_ts:
        try:
            t0 = datetime.datetime.fromisoformat(first_ts.replace("Z", "+00:00"))
            t1 = datetime.datetime.fromisoformat(last_ts.replace("Z", "+00:00"))
            wall_sec = round((t1 - t0).total_seconds())
        except Exception:
            wall_sec = None

    return {
        "first_user_text": first_user_text,
        "last_assistant_text": last_assistant_text or "",
        "wall_sec": wall_sec,
        "effort": effort_values[-1] if effort_values else None,
        "usage_by_model": usage_by_model,
        "assistant_turns": assistant_turns,
    }


_CMD_NAME_RE = re.compile(r"<command-name>(.*?)</command-name>", re.DOTALL)
_CMD_ARGS_RE = re.compile(r"<command-args>(.*?)</command-args>", re.DOTALL)
_CMD_TAG_STRIP_RE = re.compile(
    r"<command-message>.*?</command-message>\s*"
    r"|<command-name>.*?</command-name>\s*"
    r"|<command-args>.*?</command-args>\s*",
    re.DOTALL,
)


def extract_command_context(text):
    """スラッシュコマンド起動時のラッパータグ(<command-message>等、順序は不定)を剥がし、
    (command_name, タグを除いた本文) を返す。通常の自由記述文なら (None, text)。"""
    if "<command-name>" not in text:
        return None, text
    name_match = _CMD_NAME_RE.search(text)
    name = name_match.group(1).strip() if name_match else None
    args_match = _CMD_ARGS_RE.search(text)
    args = args_match.group(1).strip() if args_match else ""
    rest = _CMD_TAG_STRIP_RE.sub("", text).strip()
    if not rest and args:
        rest = args
    return name, rest


def find_project_root(cwd):
    """cwdの祖先ディレクトリを`.git`が見つかるまで遡り、プロジェクトルートに正規化する。
    見つからなければcwdをそのまま返す(サブディレクトリごとにprojectが分裂するのを防ぐ)。"""
    if not cwd:
        return cwd
    path = os.path.normpath(cwd)
    for _ in range(15):
        if os.path.isdir(os.path.join(path, ".git")):
            return path
        parent = os.path.dirname(path)
        if parent == path:
            break
        path = parent
    return cwd


def _strip_code_fence(text):
    """モデルが指示に反して```json ... ```で囲むことがあるため、その皮を剥がす。"""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def summarize(request_text, deliverable_text):
    """`claude -p` (haiku) で依頼/成果物をそれぞれ短い一文に要約する。
    失敗時は単純truncateにフォールバックする。"""
    command_name, request_text = extract_command_context(request_text)
    request_text = request_text[:SUMMARY_INPUT_CHAR_LIMIT]
    deliverable_text = deliverable_text[:SUMMARY_INPUT_CHAR_LIMIT]

    if command_name:
        # スラッシュコマンド起動時はラッパータグを剥がした上でコマンド名を明示し、
        # フォールバック時も生タグの断片ではなく意味のある文字列になるようにする。
        prompt_request_text = (
            f"(スラッシュコマンド {command_name} を実行)" + (f"\n{request_text}" if request_text else "")
        )
        fallback_request = prompt_request_text
    else:
        prompt_request_text = request_text
        fallback_request = request_text

    fallback = (
        fallback_request[:SUMMARY_OUTPUT_CHAR_LIMIT],
        deliverable_text[:SUMMARY_OUTPUT_CHAR_LIMIT],
    )
    if not deliverable_text.strip():
        return fallback

    prompt = (
        "次の開発依頼の本文と、それに対する最終的な回答本文を読み、"
        "それぞれ日本語で20〜40字程度の一文に要約してください。"
        '出力は次のJSON形式のみを返してください（説明文やコードブロック記法は不要）: '
        '{"request": "...", "deliverable": "..."}\n\n'
        f"【依頼本文】\n{prompt_request_text}\n\n【回答本文】\n{deliverable_text}"
    )
    try:
        env = os.environ.copy()
        env[GUARD_ENV] = "1"
        result = subprocess.run(
            ["claude", "-p", prompt, "--model", "haiku", "--output-format", "json"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=75,
            env=env,
        )
        payload = json.loads(result.stdout)
        text = _strip_code_fence(payload.get("result", ""))
        parsed = json.loads(text)
        req = (parsed.get("request") or "").strip()[:SUMMARY_OUTPUT_CHAR_LIMIT]
        deliv = (parsed.get("deliverable") or "").strip()[:SUMMARY_OUTPUT_CHAR_LIMIT]
        if req and deliv:
            return req, deliv
        return fallback
    except Exception:
        _log_error("summarize failed:\n" + traceback.format_exc())
        return fallback


def process_session(transcript_path, session_id, cwd):
    parsed = parse_transcript(transcript_path)

    if not parsed["first_user_text"] or parsed["assistant_turns"] < MIN_ASSISTANT_TURNS:
        return  # 実質的な依頼がなかったセッションはログしない

    request_summary, deliverable_summary = summarize(
        parsed["first_user_text"], parsed["last_assistant_text"]
    )

    entry = {
        "timestamp": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "session_id": session_id,
        "project": find_project_root(cwd),
        "effort": parsed["effort"],
        "wall_duration_sec": parsed["wall_sec"],
        "usage_by_model": parsed["usage_by_model"],
        "request_summary": request_summary,
        "deliverable_summary": deliverable_summary,
    }

    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
