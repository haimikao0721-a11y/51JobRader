import json

from ai_config import client
from ai_prompt import SYSTEM_PROMPT
from ai_tools import tools, run_tool


# ── 主循环 ────────────────────────────────────────────────
def main():
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    print("职位采集助手已启动（输入 exit 退出）")
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
