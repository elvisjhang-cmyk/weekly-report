"""
呼叫 Anthropic API 生成本週敘事:datapack.json → narrative.json

兩階段:
  Stage 1 (draft)  用 system_prompt.md 的規則 + style_examples 產出初稿
  Stage 2 (review) 把初稿丟回去,依照 system prompt 裡的「產出前自我檢查」清單校對,
                    有問題就重寫該段落,輸出修正後的最終版本

需要環境變數 ANTHROPIC_API_KEY(本機用 .env,不要把 key 貼進對話或 commit 進 git)。

用法: python3 scripts/generate_narrative.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import config

import anthropic

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
SYSTEM_PROMPT_PATH = os.path.join(SCRIPTS_DIR, "system_prompt.md")
GLOSSARY_PATH = os.path.join(ROOT, "style_examples", "glossary.md")
STYLE_EXAMPLE_PATH = os.path.join(ROOT, "style_examples", "v2_example.md")
DATAPACK_PATH = os.path.join(ROOT, config.DATAPACK_FILE)
NARRATIVE_PATH = os.path.join(ROOT, "narrative.json")

MODEL = "claude-sonnet-5"

NARRATIVE_SCHEMA = {
    "type": "object",
    "properties": {
        "headline": {"type": "string"},
        "dek": {"type": "string"},
        "tldr_items": {"type": "array", "items": {"type": "string"}, "minItems": 4, "maxItems": 4},
        "us_tag_class": {"type": "string", "enum": ["hot", "cold", "mix"]},
        "us_tag_label": {"type": "string"},
        "us_title": {"type": "string"},
        "us_body": {"type": "array", "items": {"type": "string"}},
        "btc_tag_class": {"type": "string", "enum": ["hot", "cold", "mix"]},
        "btc_tag_label": {"type": "string"},
        "btc_title": {"type": "string"},
        "btc_body": {"type": "array", "items": {"type": "string"}},
        "rotation_title": {"type": "string"},
        "rotation_body": {"type": "array", "items": {"type": "string"}},
        "watchlist": {"type": "array", "items": {"type": "string"}, "minItems": 4, "maxItems": 4},
        "poll_question": {"type": "string"},
        "poll_options": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"key": {"type": "string"}, "text": {"type": "string"}},
                "required": ["key", "text"],
            },
            "minItems": 3, "maxItems": 3,
        },
        "footer_note": {"type": "string"},
    },
    "required": [
        "headline", "dek", "tldr_items",
        "us_tag_class", "us_tag_label", "us_title", "us_body",
        "btc_tag_class", "btc_tag_label", "btc_title", "btc_body",
        "rotation_title", "rotation_body", "watchlist", "poll_question", "poll_options", "footer_note",
    ],
}


def build_system_prompt():
    with open(SYSTEM_PROMPT_PATH, "r", encoding="utf-8") as f:
        prompt = f.read()
    with open(GLOSSARY_PATH, "r", encoding="utf-8") as f:
        glossary = f.read()
    return prompt + "\n\n---\n\n" + glossary


def call_claude(client, system, user_content, label):
    resp = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=system,
        messages=[{"role": "user", "content": user_content}],
        tools=[{
            "name": "output_narrative",
            "description": f"輸出{label}",
            "input_schema": NARRATIVE_SCHEMA,
        }],
        tool_choice={"type": "tool", "name": "output_narrative"},
    )
    for block in resp.content:
        if block.type == "tool_use":
            return block.input
    raise RuntimeError(f"{label}:模型沒有回傳結構化輸出")


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print(
            "錯誤:找不到 ANTHROPIC_API_KEY 環境變數。\n"
            "請在 .env 設定後再執行(不要把 key 貼進對話或 commit 進 git)。",
            file=sys.stderr,
        )
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    with open(DATAPACK_PATH, "r", encoding="utf-8") as f:
        datapack = json.load(f)
    with open(STYLE_EXAMPLE_PATH, "r", encoding="utf-8") as f:
        style_example = f.read()

    system_prompt = build_system_prompt()

    draft_user_content = (
        f"這是本週的 datapack:\n```json\n{json.dumps(datapack, ensure_ascii=False, indent=2)}\n```\n\n"
        f"文風請參考這篇 few-shot 範例(只學語氣跟骨架,不要照抄裡面的數字):\n"
        f"```markdown\n{style_example}\n```\n\n"
        "請輸出本週週報敘事 JSON。"
    )

    print("Stage 1: 生成初稿 ...")
    draft = call_claude(client, system_prompt, draft_user_content, "週報敘事初稿")

    review_user_content = (
        "以下是你剛剛產出的週報敘事初稿 JSON,請依照 system prompt 裡的「產出前自我檢查」清單逐條核對,"
        "如果有任何一條沒通過,重寫該段落。輸出修正後的最終版本(格式不變):\n\n"
        f"```json\n{json.dumps(draft, ensure_ascii=False, indent=2)}\n```"
    )

    print("Stage 2: 依檢查清單自我校對 ...")
    final = call_claude(client, system_prompt, review_user_content, "校對後的最終週報敘事")

    with open(NARRATIVE_PATH, "w", encoding="utf-8") as f:
        json.dump(final, f, ensure_ascii=False, indent=2)

    print(f"完成 → {NARRATIVE_PATH}")


if __name__ == "__main__":
    main()
