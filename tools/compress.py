"""
上下文压缩工具
当对话历史接近 token 阈值时，将历史压缩为结构化 MD 文档，替换原上下文
"""
import json
import tiktoken


# 粗略估算：DeepSeek 用 cl100k_base 编码
_enc = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    """估算文本的 token 数"""
    return len(_enc.encode(text))


def compress_messages(
    messages: list[dict],
    max_tokens: int = 2000,
    keep_last: int = 2,
) -> tuple[list[dict], str]:
    """
    将对话历史压缩为 MD 文档，返回 (新 messages, 压缩报告)

    参数:
        messages:   完整的 messages 列表（含 system）
        max_tokens: 压缩后的 token 上限
        keep_last:  保留最近 N 轮用户-助手对话不压缩
    返回:
        new_messages:  [system + compressed_md + 最近对话]
        report:        "压缩前 X tokens → 压缩后 Y tokens，节省 Z%"
    """
    # 分离 system prompt
    system = messages[0] if messages and messages[0]["role"] == "system" else None
    rest = messages[1:] if system else messages[:]

    # 保留最近 N 轮不压缩
    tail = []
    kept = 0
    for msg in reversed(rest):
        if msg["role"] in ("user", "assistant") and not msg.get("tool_calls"):
            kept += 1
        tail.insert(0, msg)
        if kept >= keep_last * 2:
            break

    # 要压缩的部分 = 剩下的历史
    head = rest[: len(rest) - len(tail)] if tail else rest

    # 统计
    before_tokens = sum(count_tokens(json.dumps(m, ensure_ascii=False)) for m in head)

    # 压缩为 MD
    compressed = _to_md(head)

    # 如果压缩后还超限，再截断
    compressed_tokens = count_tokens(compressed)
    if compressed_tokens > max_tokens:
        lines = compressed.split("\n")
        truncated = []
        current = 0
        for line in lines:
            line_tokens = count_tokens(line)
            if current + line_tokens > max_tokens:
                truncated.append("…(以下省略)")
                break
            truncated.append(line)
            current += line_tokens
        compressed = "\n".join(truncated)

    # 组装新的 messages：system → 历史摘要(作为上下文) → 最近对话
    new_messages = []
    if system:
        new_messages.append(system)
    new_messages.append({"role": "user", "content": f"以下是之前的对话记录摘要：\n{compressed}"})
    new_messages.extend(tail)

    after_tokens = sum(count_tokens(json.dumps(m, ensure_ascii=False)) for m in new_messages)
    saved = before_tokens - compressed_tokens
    pct = (saved / before_tokens * 100) if before_tokens > 0 else 0
    report = f"压缩前 {before_tokens} tokens → 压缩后 {compressed_tokens} tokens，节省 {pct:.0f}%"

    return new_messages, report


def _to_md(messages: list[dict]) -> str:
    """将消息列表转为结构化 MD 文档"""
    blocks = []

    for msg in messages:
        role = msg["role"]
        content = msg.get("content", "") or ""

        if role == "user":
            blocks.append(f"> **用户**: {content[:200]}")

        elif role == "assistant":
            if msg.get("tool_calls"):
                for tc in msg["tool_calls"]:
                    name = tc["function"]["name"]
                    args = tc["function"]["arguments"]
                    blocks.append(f"> **AI 调用了 {name}** — 参数: {args[:150]}")
            elif content:
                blocks.append(f"> **AI**: {content[:300]}")

        elif role == "tool":
            # 工具返回结果，截取关键信息
            data = content
            if len(data) > 200:
                data = data[:200] + "…"
            blocks.append(f"> **工具返回**: {data}")

    return "\n\n".join(blocks)


def check_and_compress(
    messages: list[dict],
    warn_threshold: int = 180_000,
    max_tokens: int = 2000,
) -> tuple[list[dict], str | None]:
    """
    检查 token 用量，接近阈值时自动压缩

    返回:
        (messages, report)  — report 为 None 表示无需压缩
    """
    total = count_tokens(json.dumps(messages, ensure_ascii=False))
    if total < warn_threshold:
        return messages, None

    new_msgs, report = compress_messages(messages, max_tokens=max_tokens)
    return new_msgs, report
