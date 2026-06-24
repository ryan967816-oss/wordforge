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


LESSON_BLOCKS: list[dict] = [
    {
        "title": "开场：女儿的问题把战争逼回家庭",
        "start_segment": 0,
        "end_segment": 15,
        "core_zh": "这一页不是先讲战场，而是先讲女儿问父亲有没有杀过人；战争记忆被带进亲密关系里。",
        "why_good_zh": "强处在 frame：孩子的问题很简单，成年人却无法简单回答，所以整篇课文的道德压力一下成立。",
        "watch_zh": [
            "asked if I had ever killed anyone 是间接问句，ever 把问题推向一生经验。",
            "what happened / what I remember happening 的差别很重要：作者不是只交代事实，而是在承认记忆会变形。",
        ],
        "vocab": [
            {"english": "war stories", "chinese": "战争故事；创伤记忆的叙述", "usage": "keep writing these war stories"},
            {"english": "pretend", "chinese": "假设；暂且当作", "usage": "pretend she's a grown up"},
            {"english": "exactly what happened", "chinese": "事情到底怎么发生", "usage": "tell her exactly what happened"},
            {"english": "remember happening", "chinese": "记忆中发生的样子", "usage": "what I remember happening"},
        ],
    },
    {
        "title": "倒带：伏击场景被重新搭起来",
        "start_segment": 16,
        "end_segment": 31,
        "core_zh": "作者先承认结果：我扔了手榴弹并杀了他；然后倒带到午夜、伏击点、雾、值班和等待。",
        "why_good_zh": "强处在非线性叙事：先给你结果，再让你回到身体如何一步步进入那个结果。",
        "watch_zh": [
            "Or, to go back 是叙事倒带，不是普通补充。",
            "switching off every two hours 是两人轮换值守；这种 routine 让后面的杀伤显得更日常、更可怕。",
        ],
        "vocab": [
            {"english": "ambush", "chinese": "伏击", "usage": "ambush site"},
            {"english": "platoon", "chinese": "排；小队", "usage": "the whole platoon"},
            {"english": "dense brush", "chinese": "浓密灌木", "usage": "spread out in the dense brush"},
            {"english": "grenade", "chinese": "手榴弹", "usage": "three grenades"},
            {"english": "pins", "chinese": "保险销", "usage": "pins had already been straightened"},
            {"english": "kneeled", "chinese": "跪着", "usage": "kneeled there and waited"},
        ],
    },
    {
        "title": "敌人先被写成一个人",
        "start_segment": 32,
        "end_segment": 45,
        "core_zh": "清晨、雾、蚊子、一个年轻人出现；作者没有先把他写成 enemy，而是写他的衣服、姿态和放松。",
        "why_good_zh": "强处在去标签化：对方不是抽象敌人，而是一个有身体姿态、走路节奏、甚至像从雾里出来的人。",
        "watch_zh": [
            "He seemed at ease 是关键：他看起来放松，这让后面的死亡更难被战斗逻辑完全解释。",
            "part of the morning fog or my own imagination 把现实和心理影像叠在一起。",
        ],
        "vocab": [
            {"english": "slivers", "chinese": "细片；一点一点", "usage": "in tiny slivers"},
            {"english": "repellent", "chinese": "驱虫剂", "usage": "ask for some repellent"},
            {"english": "ammunition belt", "chinese": "弹药带", "usage": "a gray ammunition belt"},
            {"english": "stooped", "chinese": "微微弯曲的", "usage": "shoulders were slightly stooped"},
            {"english": "at ease", "chinese": "放松；不戒备", "usage": "He seemed at ease"},
            {"english": "muzzled down", "chinese": "枪口朝下", "usage": "weapon in one hand, muzzled down"},
        ],
    },
    {
        "title": "身体先动，解释后来才追上",
        "start_segment": 46,
        "end_segment": 61,
        "core_zh": "这一页的核心是自动反应：胃里的恐惧、已经拔掉保险、已经蹲起，身体比道德语言更快。",
        "why_good_zh": "作者连续否定 hate/enemy/morality/politics/duty，把通常战争解释全部撤掉，只留下身体机制。",
        "watch_zh": [
            "It was entirely automatic 是关键判词：不是说没有责任，而是说行动发生在完整解释之前。",
            "before telling myself to throw it 表示自我命令迟到了，身体已经做完。",
        ],
        "vocab": [
            {"english": "crouch", "chinese": "蹲伏", "usage": "come up to a crouch"},
            {"english": "automatic", "chinese": "自动的；未经思考的", "usage": "It was entirely automatic"},
            {"english": "ponder", "chinese": "认真思量", "usage": "did not ponder issues"},
            {"english": "morality", "chinese": "道德", "usage": "issues of morality"},
            {"english": "evaporate", "chinese": "蒸发；消失", "usage": "just evaporate"},
            {"english": "lob", "chinese": "高抛", "usage": "lob at high"},
        ],
    },
    {
        "title": "爆炸之前的慢镜头",
        "start_segment": 62,
        "end_segment": 78,
        "core_zh": "手榴弹在记忆里像镜头定格；他想警告对方，但时间已经越过了可以挽回的点。",
        "why_good_zh": "强处在声音反差：爆炸不是大片式轰鸣，而是 popping noise 和 small white puff，越小越冷。",
        "watch_zh": [
            "camera had clicked 是创伤记忆的定格感：某一瞬间永远停在那里。",
            "It occurred to me then that... 是意识终于追上现实：他才明白那个人要死。",
        ],
        "vocab": [
            {"english": "freeze", "chinese": "冻结；定格", "usage": "seeming to freeze above me"},
            {"english": "wisps", "chinese": "缕；丝", "usage": "little wisps of fog"},
            {"english": "hesitated", "chinese": "迟疑", "usage": "then he hesitated"},
            {"english": "swiveling", "chinese": "转身；旋转", "usage": "swiveling to his right"},
            {"english": "popping noise", "chinese": "砰的一声；不大的爆声", "usage": "made a popping noise"},
            {"english": "star-shaped", "chinese": "星形的", "usage": "a huge star-shaped hole"},
        ],
    },
    {
        "title": "peril：真正折磨他的不是危险",
        "start_segment": 79,
        "end_segment": 88,
        "core_zh": "这里最难：他说 there was no real peril，意思是事后看来对方大概率会走过去；所以杀人不再能被“自卫危险”轻易包住。",
        "why_good_zh": "peril 在 grenade 之后出现，力量正来自反差：武器很危险，但叙述者否认当时有真正危险，罪感因此更尖。",
        "watch_zh": [
            "good kill 是军事安慰语，试图把事件塞回战争逻辑；但 narrator 的心不接受。",
            "The words seemed far too complicated 表示所有解释都压不过眼前身体事实。",
        ],
        "vocab": [
            {"english": "peril", "chinese": "危险；迫近的威胁", "usage": "There was no real peril"},
            {"english": "would have passed by", "chinese": "本来会走过去", "usage": "would have passed by"},
            {"english": "good kill", "chinese": "军事语境里的合理击杀", "usage": "it was a good kill"},
            {"english": "shape up", "chinese": "振作；别垮掉", "usage": "should shape up"},
            {"english": "reversed", "chinese": "情况反过来", "usage": "if things were reversed"},
            {"english": "gape", "chinese": "张口呆看", "usage": "gape at the fact"},
        ],
    },
    {
        "title": "结尾：记忆没有被解决，只是不断返回",
        "start_segment": 89,
        "end_segment": 97,
        "core_zh": "多年以后，他仍然没有整理完这件事；那个年轻人会在普通生活里从雾中重新走出来。",
        "why_good_zh": "强处在循环结构：开头说 keep writing war stories，结尾让影像反复回来，说明写作不是解决，而是承受未解决。",
        "watch_zh": [
            "sort it out 是心理整理，不是整理物品。",
            "dwell on it 是反复想着它；作者说 try not to dwell，但影像仍然回来。",
        ],
        "vocab": [
            {"english": "sort it out", "chinese": "理清；整理明白", "usage": "haven't finished sorting it out"},
            {"english": "forgive myself", "chinese": "原谅自己", "usage": "Sometimes I forgive myself"},
            {"english": "dwell on", "chinese": "反复想着；沉溺于", "usage": "try not to dwell on it"},
            {"english": "ordinary hours", "chinese": "日常时刻", "usage": "ordinary hours of life"},
            {"english": "secret thought", "chinese": "秘密念头", "usage": "smile at some secret thought"},
            {"english": "bends back", "chinese": "弯回去", "usage": "where it bends back into the fog"},
        ],
    },
]


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
        "blocks": LESSON_BLOCKS,
        "segments": baked_segments,
        "text_en": " ".join(s.get("text", "") for s in segments),
    }

    out = reading_packages.local_package_dir() / f"{args.id}.jsonl"
    out.write_text(json.dumps(package, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"path": str(out), "segments": len(baked_segments)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
