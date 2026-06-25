import json
import argparse
import sys
import os

# 确保 agent/ 目录下的模块能正常导入
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ai_config import client
from ai_prompt import SYSTEM_PROMPT
from ai_tools import get_tools, run_tool
from tools.compress import check_and_compress


def _inject_resume(path: str) -> str:
    """读取简历文件，返回注入文本"""
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    from resume import load_resume

    return load_resume(path)


# ── 主循环 ────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--resume", help="简历文件路径（.pdf / .txt / .md）")
    parser.add_argument(
        "--max-context", type=int, default=256000,
        help="最大上下文 token 数（默认 256000），压缩阈值自动设为 70%%",
    )
    args, _ = parser.parse_known_args()

    system_content = SYSTEM_PROMPT
    if args.resume:
        resume_text = _inject_resume(args.resume)
        system_content += f"\n\n## 用户简历\n{resume_text}"

    messages = [{"role": "system", "content": system_content}]
    warn_threshold = int(args.max_context * 0.7)
    print(f"职位采集助手已启动（最大上下文 {args.max_context:,} tokens，压缩阈值 {warn_threshold:,} tokens）")
    if args.resume:
        print(f"📄 已加载简历: {args.resume}")
    print("=" * 50)
    while True:
        user_input = input("\n你: ").strip()
        if user_input.lower() in ("exit", "quit"):
            break
        if not user_input:
            continue

        messages.append({"role": "user", "content": user_input})

        while True:
            response = client.chat.completions.create(
                model="deepseek-v4-pro",
                messages=messages,
                tools=get_tools(),
                tool_choice="auto",
            )
            msg = response.choices[0].message

            if not msg.tool_calls:
                messages.append(msg)
                print("\n🤖 ", end="", flush=True)
                stream = client.chat.completions.create(
                    model="deepseek-v4-pro",
                    messages=messages,
                    stream=True,
                )
                reply = ""
                for chunk in stream:
                    delta = chunk.choices[0].delta
                    if delta and delta.content:
                        print(delta.content, end="", flush=True)
                        reply += delta.content
                print()
                messages.append({"role": "assistant", "content": reply})

                # 回复后检查 token 用量
                messages, report = check_and_compress(messages, warn_threshold=warn_threshold)
                if report:
                    print(f"\n[压缩] {report}")
                break

            messages.append(
                {
                    "role": msg.role,
                    "content": msg.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                            "type": "function",
                        }
                        for tc in msg.tool_calls
                    ],
                }
            )

            for tc in msg.tool_calls:
                name = tc.function.name
                args = json.loads(tc.function.arguments)
                print(f"\n调用 {name}({json.dumps(args, ensure_ascii=False)})...")

                try:
                    result = run_tool(name, args)
                except Exception as e:
                    error_info = {
                        "error": f"{type(e).__name__}: {str(e)[:300]}",
                        "hint": "请根据错误信息决定：换参数重试、换其他工具、或告知用户当前不可用",
                    }
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(error_info, ensure_ascii=False),
                    })
                    print(f"工具异常: {type(e).__name__}")
                    continue

                print(f"返回 {len(result) if isinstance(result, list) else 1} 条结果")

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(result, ensure_ascii=False),
                    }
                )

            # 工具返回后检查 token 用量，接近阈值则压缩
            messages, report = check_and_compress(messages, warn_threshold=warn_threshold)
            if report:
                print(f"\n[压缩] {report}")


if __name__ == "__main__":
    main()
