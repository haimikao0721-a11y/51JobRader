import json
import argparse
import sys
import os

# 确保 agent/ 目录下的模块能正常导入
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ai_config import client
from ai_prompt import SYSTEM_PROMPT
from ai_tools import tools, run_tool


def _inject_resume(path: str) -> str:
    """读取简历文件，返回注入文本"""
    import sys
    sys.path.insert(0, "..")
    from resume import load_resume

    return load_resume(path)


# ── 主循环 ────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--resume", help="简历文件路径（.pdf / .txt / .md）")
    args, _ = parser.parse_known_args()

    system_content = SYSTEM_PROMPT
    if args.resume:
        resume_text = _inject_resume(args.resume)
        system_content += f"\n\n## 用户简历\n{resume_text}"

    messages = [{"role": "system", "content": system_content}]
    print("职位采集助手已启动（输入 exit 退出）")
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
                tools=tools,
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
                result = run_tool(name, args)
                print(f"获取到 {len(result)} 个职位")

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(result, ensure_ascii=False),
                    }
                )


if __name__ == "__main__":
    main()
