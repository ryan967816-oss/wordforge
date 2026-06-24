#!/usr/bin/env python3
"""Bake a local-only reading package from an existing Listening Reader transcript.

This writes to data/reading_packages/local/, which is gitignored. It is for the
learner's local textbook/audio material and should not be committed.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from wordforge import listening, reading_packages  # noqa: E402


COMMENTS: dict[int, tuple[str, str]] = {
    3: (
        "When she was nine 是时间状语；asked if... 是孩子把战争故事逼回现实的问题。",
        "美国战争文学常用“孩子的问题”打开道德压力：不是解释历史，而是问你本人到底做过什么。",
    ),
    6: (
        "You keep writing... 是女儿的直接引语；keep + -ing 表示反复做、停不下来。",
        "war stories 在美国文化里不是单纯战斗爽文，经常是创伤、责任和记忆的容器。",
    ),
    9: (
        "did what seemed right = 做了当时看起来正确的事；which was to say... 把动作解释成一句谎言。",
        "这里重要的是父亲的保护性谎言：他不是忘了，而是不知道怎样把成人的道德重量交给孩子。",
    ),
    13: (
        "what happened / what I remember happening 并列；第二个更诚实，因为记忆本身会变形。",
        "这类叙事常区分事实与记忆：作者不是只讲事件，而是在审问自己还能怎样讲这件事。",
    ),
    15: (
        "This is why... 不是简单原因句，而是把写作动机钉在未解决的记忆上。",
        "写 war stories 是一种反复回到现场的行为：不是已经懂了才写，而是因为还没整理完才写。",
    ),
    20: (
        "Or, to go back 是叙事倒带；作者从承认杀人退回到午夜前的场景。",
        "美国课堂常教这种 non-linear narration：心理顺序比时间顺序更重要。",
    ),
    24: (
        "while the other slept, switching off every two hours 是巡逻值守的 routine。",
        "这不是英雄叙事，而是把杀人放回疲惫、值班、蚊子和自动反应的日常机制里。",
    ),
    31: (
        "kneeled there and waited 把动作压低；for maybe half an hour 让等待变长。",
        "这一段的文化门槛是 Vietnam War 叙事里的 ambush tension：危险来自看不清、等太久、身体先反应。",
    ),
    40: (
        "at ease = 放松、不紧张；这让后面的杀伤更难被正当化。",
        "对方不是抽象 enemy，而是一个自然走路的人；文本在拆掉“敌人”这个方便标签。",
    ),
    52: (
        "There were no thoughts about killing 是关键否定；动作发生时没有完整道德叙事。",
        "这解释了为什么中文大意不够：作者想让你进入自动反应和事后罪感之间的裂缝。",
    ),
    58: (
        "before telling myself to throw it = 在我告诉自己扔之前已经扔了。",
        "这是核心心理机制：身体行动早于自我命令，所以责任感变得更复杂，而不是消失。",
    ),
    70: (
        "It occurred to me then that... 是事后意识突然抵达。",
        "这一刻不是战术判断，而是道德认知：他才真正意识到那个人要死。",
    ),
    78: (
        "good kill 是军事语言；shape up 是让他振作、别崩。",
        "美国战争文化里这种安慰很重要也很残酷：同伴给他一个可用解释，但他的心不接受。",
    ),
    82: (
        "The words seemed far too complicated = 那些解释太复杂，压不过眼前事实。",
        "这句话说明为什么你只看中文摘要会失去震动：真正的对象不是概念，而是 fact of the body。",
    ),
    88: (
        "Even now I haven't finished sorting it out 是多年后仍未完成的整理。",
        "这也是文学的功能：不是把创伤解决掉，而是给 unresolved attention 一个形式。",
    ),
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--index", type=int, default=0, help="Listening Reader audio index to bake")
    p.add_argument("--id", default="lesson-ambush-local")
    p.add_argument("--title", default="Ambush · local lesson")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    files = listening.index_audio()
    if not (0 <= args.index < len(files)):
        raise SystemExit(f"audio index out of range: {args.index}")

    segments = listening.transcribe(files[args.index])
    baked_segments = []
    for i, seg in enumerate(segments):
        component, comment = COMMENTS.get(i, ("", ""))
        baked_segments.append(
            {
                "index": i,
                "start_ms": seg.get("start_ms", 0),
                "end_ms": seg.get("end_ms", 0),
                "text_en": seg.get("text", ""),
                "component_zh": component,
                "codex_comment": comment,
                "palette": [],
            }
        )

    package = {
        "id": args.id,
        "title": args.title,
        "book": "Local lesson text",
        "source": "Local Listening Reader transcript",
        "route": "lesson",
        "category": "lesson",
        "local": True,
        "level": "B2-C1",
        "audio_index": args.index,
        "audio_name": str(files[args.index].name),
        "why_selected": "A local classroom/literary text where the hard part is cultural and moral framing, not only vocabulary.",
        "context_note": "Local-only package generated from the existing transcript cache; not committed.",
        "target_structures": ["framed memory", "reported speech", "past perfect", "war narrative", "moral aftermath"],
        "glosses": [
            {"word": "ambush", "chinese": "伏击", "hint": "hidden attack from a concealed position"},
            {"word": "platoon", "chinese": "排；小队", "hint": "military unit"},
            {"word": "grenade", "chinese": "手榴弹", "hint": "small explosive weapon"},
            {"word": "shape up", "chinese": "振作；像样点", "hint": "informal pressure to regain control"},
            {"word": "sort it out", "chinese": "理清；整理明白", "hint": "mentally process something unresolved"},
        ],
        "vocab_targets": ["ambush", "platoon", "grenade", "automatic", "peril", "dwell"],
        "grammar": [
            "The narrative moves between the daughter frame and the remembered war scene.",
            "Past perfect marks actions already completed before the narrator can morally process them.",
            "The repeated negatives remove easy justification: no hatred, no enemy image, no abstract duty.",
        ],
        "codex_comment_zh": "这篇本地课文的难点不是“发生了什么”，而是美国战争叙事里个人责任、创伤记忆和写作动机怎样缠在一起。",
        "codex_comment_en": "The passage is not asking you to admire battle; it asks why a memory keeps returning when ordinary explanations fail.",
        "segments": baked_segments,
        "text_en": " ".join(s.get("text", "") for s in segments),
    }

    out = reading_packages.local_package_dir() / f"{args.id}.jsonl"
    out.write_text(json.dumps(package, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"path": str(out), "segments": len(baked_segments)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
