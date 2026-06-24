#!/usr/bin/env python3
"""Bake local-only Reader lesson packages from the California Edge audio shelf.

This writes JSONL packages under data/reading_packages/local/, which is
gitignored. The script is intentionally practical: it turns local textbook audio
into small page-reader blocks with enough Chinese scaffolding to start reading
tonight, then those packages can be hand-thickened later.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from wordforge import listening, reading_packages  # noqa: E402


# 0-based indices in listening.index_audio(). These are real selection
# recordings, not the shorter selection summaries.
DEFAULT_INDICES = [358, 359, 360, 361, 362, 363, 114, 115, 116, 117]

TITLE_OVERRIDES = {
    "edge_f_sr_cd1_01_first_names_p14": "First Names",
    "edge_f_sr_cd1_02_romeo_and_juliet_p21": "Romeo and Juliet · balcony scene",
    "edge_f_sr_cd1_03_growing_together_p36": "Growing Together",
    "edge_f_sr_cd1_04_my_people_p43": "My People",
    "edge_f_sr_cd1_05ways_to_know_you_p54": "Ways to Know You",
    "edge_f_sr_cd1_06_who_is_she_p63": "Who Is She?",
    "edge_b_sr_cd1_01": "The Good Samaritan · Part 1",
    "edge_b_sr_cd1_02": "The Good Samaritan · Part 2",
    "edge_b_sr_cd1_03": "The Good Samaritan · Part 3",
    "edge_b_sr_cd1_04": "The World Is in Their Hands",
}

LESSON_NOTES: list[tuple[str, dict[str, Any]]] = [
    (
        "samaritan",
        {
            "why": "这类寓言课文的重点不是记住剧情，而是看见谁被视为 neighbor：道德判断常常藏在一个具体行动里。",
            "structures": ["parable", "reported action", "moral contrast", "question-and-answer frame"],
            "watch": [
                "注意人物顺序：谁看见、谁绕开、谁停下来，动作本身就是道德判断。",
                "如果出现 went by / passed by / took care of，先抓动作链，不要急着翻抽象道德。",
            ],
            "vocab": ["neighbor", "wounded", "journey", "compassion", "priest", "Samaritan", "mercy"],
        },
    ),
    (
        "romeo",
        {
            "why": "Shakespeare 的难点是古英语式词序和隐喻；先抓谁在说、对谁说、用什么图像表达欲望。",
            "structures": ["dramatic speech", "metaphor", "archaic word order", "address"],
            "watch": [
                "舞台对白里 O / thou / wherefore 一类词不是装饰，而是在制造直接呼唤的强度。",
                "不要逐词硬拆；先抓爱情对象、阻碍、比喻三件事。",
            ],
            "vocab": ["wherefore", "deny", "refuse", "name", "swear", "light", "window"],
        },
    ),
    (
        "first names",
        {
            "why": "这类文化课文通常在讲称呼背后的亲密度、平等感和社会距离；first name 不是单纯名字问题。",
            "structures": ["social custom", "contrast", "example chain", "politeness register"],
            "watch": [
                "遇到 call someone by... 要想：这里在讲称呼方式，不只是叫名字。",
                "注意 formal / informal 的切换；它通常对应权力距离或关系远近。",
            ],
            "vocab": ["formal", "informal", "custom", "address", "polite", "relationship", "stranger"],
        },
    ),
    (
        "my people",
        {
            "why": "这类诗/散文的强处常在重复和身份感：people 不是人口，而是归属、血缘、语言和共同记忆。",
            "structures": ["poetic repetition", "identity", "image list", "speaker stance"],
            "watch": [
                "重复出现的 ordinary nouns 往往不是简单重复，而是在堆出归属感。",
                "如果句子很短，优先听节奏和并列，不要只找主谓宾。",
            ],
            "vocab": ["people", "belong", "heritage", "voice", "memory", "skin", "pride"],
        },
    ),
    (
        "growing together",
        {
            "why": "标题已经给出主轴：growth 不是一个人单独变强，而是在关系里互相塑形。",
            "structures": ["growth metaphor", "relationship change", "time markers", "cause and effect"],
            "watch": [
                "注意 together 修饰的是成长方式：重点在共同经历如何改变人。",
                "看到 used to / began to / learned to 先标时间变化。",
            ],
            "vocab": ["grow", "together", "change", "learn", "share", "understand", "support"],
        },
    ),
    (
        "ways to know you",
        {
            "why": "这类题目通常在讲理解一个人不能只靠信息，而要靠行动、选择、关系和持续观察。",
            "structures": ["list structure", "ways of knowing", "evidence", "contrast"],
            "watch": [
                "ways to know you 里的 know 是理解一个人，不只是知道事实。",
                "注意 by + doing 结构：它常说明理解从哪里来。",
            ],
            "vocab": ["know", "understand", "notice", "gesture", "choice", "habit", "trust"],
        },
    ),
    (
        "who is she",
        {
            "why": "这类身份题常用悬念推进：问题不是名字，而是一个人怎样被别人认识、误读或重新看见。",
            "structures": ["identity question", "description", "revelation", "point of view"],
            "watch": [
                "Who is she? 先不要急着找姓名；看文本如何一点点给线索。",
                "形容词和动作细节通常承担人物判断。",
            ],
            "vocab": ["identity", "recognize", "describe", "appearance", "secret", "realize", "reveal"],
        },
    ),
    (
        "world is in their hands",
        {
            "why": "标题带 responsibility 的味道：world in their hands 通常把年轻人、行动和未来责任连在一起。",
            "structures": ["responsibility metaphor", "collective subject", "future tense", "problem-solution"],
            "watch": [
                "in their hands 是隐喻：不是手里真的拿着世界，而是承担影响未来的责任。",
                "遇到 can / must / should，先判断作者是在给能力、义务还是建议。",
            ],
            "vocab": ["responsibility", "future", "protect", "environment", "community", "action", "choice"],
        },
    ),
]

COMMON_GLOSSARY: dict[str, tuple[str, str]] = {
    "address": ("称呼；对某人说话", "how people speak to or name each other"),
    "answer": ("回答；回应", "a reply, or the thing that resolves a question"),
    "appearance": ("外表；出现方式", "how someone looks or first shows up"),
    "belong": ("属于；有归属", "to feel part of a group or place"),
    "character": ("人物；性格", "a person in a story, or someone's qualities"),
    "characters": ("人物；角色", "people in a story or play"),
    "choice": ("选择", "a decision that reveals values"),
    "community": ("共同体；社区", "a group of people connected by place or care"),
    "compassion": ("同情并愿意行动", "feeling another's pain and acting on it"),
    "custom": ("习俗；惯例", "what people in a culture usually do"),
    "deny": ("否认；拒绝承认", "to refuse or say no to something"),
    "different": ("不同的", "not the same; often a contrast signal"),
    "environment": ("环境", "the natural or social world around people"),
    "everywhere": ("到处；无处不在", "in many or all places"),
    "excerpt": ("节选；摘录", "a selected part from a longer work"),
    "expository": ("说明性的", "writing that explains rather than tells a story"),
    "family": ("家庭；家族", "kinship group; in literature often loyalty or conflict"),
    "famous": ("著名的", "well known by many people"),
    "formal": ("正式的", "used when distance or politeness matters"),
    "friends": ("朋友；亲近的人", "people with social closeness"),
    "gesture": ("姿态；小动作", "a small action that shows feeling or intention"),
    "habit": ("习惯", "a repeated way of doing things"),
    "heritage": ("传承；文化遗产", "what is received from family or culture"),
    "hurricane": ("飓风", "a powerful tropical storm"),
    "identity": ("身份；我是谁", "who someone is in a social or inner sense"),
    "informal": ("非正式的；亲近的", "used when people are close or relaxed"),
    "journey": ("旅程", "a movement through space, often also moral change"),
    "know": ("认识；理解", "to know facts, or to understand a person"),
    "mercy": ("怜悯；宽恕式的帮助", "kindness shown to someone in trouble"),
    "metaphor": ("隐喻", "one thing described as another to carry feeling"),
    "name": ("名字；命名/身份标签", "a word for a person; often tied to identity"),
    "neighbor": ("邻人；应被关照的人", "not only a nearby person, but someone you owe care"),
    "non-fiction": ("非虚构", "writing based on facts rather than invented plot"),
    "polite": ("礼貌的", "socially respectful"),
    "priest": ("祭司；神职人员", "a religious figure"),
    "pride": ("自豪；尊严", "a strong sense of worth"),
    "recognize": ("认出；承认", "to see what someone or something really is"),
    "refuse": ("拒绝", "to say no or not accept"),
    "relationship": ("关系", "connection between people"),
    "responsibility": ("责任", "what one must care for or answer for"),
    "reveal": ("揭示；显露", "to make something hidden known"),
    "samaritan": ("撒玛利亚人", "in the parable, the outsider who actually helps"),
    "share": ("分享；共同拥有", "to have or do something with others"),
    "stranger": ("陌生人", "someone not known or not inside the group"),
    "swear": ("发誓", "to make a serious promise"),
    "trust": ("信任", "to rely on someone or something"),
    "understand": ("理解", "to grasp meaning, motive, or feeling"),
    "unique": ("独特的", "one of a kind; not interchangeable"),
    "wherefore": ("为什么；为何", "archaic why, not where"),
    "window": ("窗；戏剧中也常是看见/距离的界面", "literal window, often a frame for seeing"),
    "wounded": ("受伤的", "hurt, especially physically"),
}

STOPWORDS = {
    "about",
    "after",
    "again",
    "also",
    "begins",
    "because",
    "before",
    "being",
    "could",
    "every",
    "first",
    "from",
    "have",
    "into",
    "just",
    "listen",
    "like",
    "little",
    "more",
    "much",
    "only",
    "other",
    "saldana",
    "people",
    "people's",
    "should",
    "some",
    "story",
    "that",
    "their",
    "there",
    "these",
    "thing",
    "those",
    "through",
    "under",
    "very",
    "what",
    "when",
    "where",
    "which",
    "while",
    "with",
    "would",
    "your",
    "today",
    "going",
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--indices", default="", help="Comma-separated 0-based audio indices")
    p.add_argument("--count", type=int, default=10, help="How many default lessons to bake")
    p.add_argument("--workers", type=int, default=2, help="Concurrent transcriptions")
    p.add_argument("--force", action="store_true", help="Overwrite existing local packages")
    return p.parse_args()


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "lesson"


def clean_stem(path: Path) -> str:
    stem = path.stem.lower().replace("&", " and ")
    stem = re.sub(r"[^a-z0-9]+", "_", stem).strip("_")
    return stem


def title_for(path: Path) -> str:
    stem = clean_stem(path)
    for key, title in TITLE_OVERRIDES.items():
        if key in stem:
            return title
    title = re.sub(r"edge_[a-z]_sr_cd\d+_\d+", "", stem).strip("_")
    title = re.sub(r"_p\d+$", "", title)
    title = re.sub(r"_+", " ", title).strip()
    return title.title() if title else path.stem


def note_for(title: str, path: Path) -> dict[str, Any]:
    haystack = f"{title} {path}".lower()
    for needle, note in LESSON_NOTES:
        if needle in haystack:
            return note
    return {
        "why": "这篇先当作可读课文：先抓人物、动作、转折和作者态度，再把不懂的词点出来问。",
        "structures": ["narrative", "description", "contrast", "sentence rhythm"],
        "watch": [
            "先抓 who did what，再看作者为什么选择这个细节。",
            "遇到长句先切成动作链，不要在第一个生词处停死。",
        ],
        "vocab": [],
    }


def group_segments(segments: list[dict[str, Any]]) -> list[tuple[int, int]]:
    groups: list[tuple[int, int]] = []
    start = 0
    chars = 0
    for i, seg in enumerate(segments):
        chars += len(str(seg.get("text", "") or seg.get("text_en", "")))
        count = i - start + 1
        at_end = i == len(segments) - 1
        if at_end or count >= 3 or chars >= 520:
            groups.append((start, i))
            start = i + 1
            chars = 0
    return groups


def sentences_text(segments: list[dict[str, Any]], start: int, end: int) -> str:
    return " ".join(str(s.get("text", "") or s.get("text_en", "")).strip() for s in segments[start : end + 1]).strip()


def short_focus(text: str) -> str:
    words = re.findall(r"[A-Za-z][A-Za-z'-]*", text)
    focus = " ".join(words[:7])
    return focus + ("..." if len(words) > 7 else "")


def token_hits(text: str, wanted: list[str]) -> list[str]:
    norm = " " + re.sub(r"[^a-z0-9'-]+", " ", text.lower()) + " "
    hits: list[str] = []
    for term in wanted:
        if f" {term.lower()} " in norm and term not in hits:
            hits.append(term)
    return hits


def fallback_words(text: str, limit: int) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for word in re.findall(r"[A-Za-z][A-Za-z'-]{5,}", text):
        if word[:1].isupper():
            continue
        low = word.lower().strip("'")
        if low in STOPWORDS or low in seen:
            continue
        seen.add(low)
        out.append(word)
        if len(out) >= limit:
            break
    return out


def vocab_items(text: str, note: dict[str, Any]) -> list[dict[str, str]]:
    words = token_hits(text, list(note.get("vocab", []) or []))
    words.extend(w for w in fallback_words(text, 6) if w.lower() not in {x.lower() for x in words})
    items: list[dict[str, str]] = []
    for word in words[:8]:
        key = word.lower()
        chinese, hint = COMMON_GLOSSARY.get(key, ("这一页的关键词；先按上下文理解", "ask this word in its sentence"))
        items.append({"english": word, "chinese": chinese, "usage": hint})
    return items


def page_comment(page: int, text: str, note: dict[str, Any]) -> tuple[str, str, list[str]]:
    focus = short_focus(text)
    core = f"第 {page} 页先抓主干：这一小块围绕 “{focus}” 展开，读的时候先标人物/动作/态度，再处理生词。"
    why = str(note.get("why", ""))
    watch = list(note.get("watch", []) or [])[:2]
    if re.search(r"\b(but|however|although|though|yet)\b", text, re.I):
        watch.append("这一页有转折词；转折后通常是作者真正要你注意的压力点。")
    if re.search(r"\b(should|must|can|may|might|would)\b", text, re.I):
        watch.append("注意情态动词：它在标能力、义务、可能性或态度，不只是语法形式。")
    return core, why, watch[:4]


def build_package(index: int, path: Path, force: bool = False) -> dict[str, Any]:
    title = title_for(path)
    pid = f"lesson-edge-{index + 1:03d}-{slugify(title)}"
    out = reading_packages.local_package_dir() / f"{pid}.jsonl"
    if out.exists() and not force:
        row = json.loads(out.read_text(encoding="utf-8").splitlines()[0])
        return {"id": pid, "path": str(out), "title": row.get("title", title), "segments": len(row.get("segments", [])), "cached": True}

    segments = listening.transcribe(path)
    note = note_for(title, path)
    baked_segments = [
        {
            "index": i,
            "start_ms": seg.get("start_ms", 0),
            "end_ms": seg.get("end_ms", 0),
            "text_en": str(seg.get("text", "")).strip(),
            "component_zh": "",
            "codex_comment": "",
            "palette": [],
        }
        for i, seg in enumerate(segments)
    ]
    blocks = []
    for page, (start, end) in enumerate(group_segments(segments), 1):
        text = sentences_text(segments, start, end)
        core, why, watch = page_comment(page, text, note)
        blocks.append(
            {
                "index": page - 1,
                "title": f"Page {page} · {short_focus(text)}",
                "start_segment": start,
                "end_segment": end,
                "text_en": text,
                "core_zh": core,
                "why_good_zh": why,
                "watch_zh": watch,
                "vocab": vocab_items(text, note),
            }
        )

    top_vocab = vocab_items(" ".join(s.get("text_en", "") for s in baked_segments), note)
    package = {
        "id": pid,
        "title": title,
        "book": "California Edge · local lesson shelf",
        "source": f"Local selection recording: {path.name}",
        "route": "lesson",
        "category": "lesson",
        "local": True,
        "level": "B1-C1",
        "audio_index": index,
        "audio_name": path.name,
        "why_selected": "A real local textbook selection recording; baked into small pages so the learner can read with audio instead of fighting one long transcript.",
        "context_note": "Local-only package generated from the user's California Edge audio shelf; not committed.",
        "target_structures": list(note.get("structures", []) or []),
        "glosses": [
            {"word": item["english"], "chinese": item["chinese"], "hint": item["usage"]}
            for item in top_vocab[:8]
        ],
        "vocab_targets": [item["english"] for item in top_vocab[:8]],
        "grammar": [
            "Read each page as a small action/thought unit before drilling individual words.",
            "When the audio moves faster than comprehension, use the page title and watch notes as the mental handle.",
            "Ask selected words from the page instead of memorizing isolated choices.",
        ],
        "codex_comment_zh": str(note.get("why", "")),
        "codex_comment_en": "This is a starter scaffold: enough support to begin reading tonight, with room for later hand-curated commentary.",
        "blocks": blocks,
        "segments": baked_segments,
        "text_en": " ".join(s.get("text_en", "") for s in baked_segments),
    }
    out.write_text(json.dumps(package, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"id": pid, "path": str(out), "title": title, "segments": len(baked_segments), "blocks": len(blocks), "cached": False}


def parse_indices(raw: str, count: int) -> list[int]:
    if raw.strip():
        return [int(x.strip()) for x in raw.split(",") if x.strip()]
    return DEFAULT_INDICES[:count]


def main() -> int:
    args = parse_args()
    files = listening.index_audio()
    indices = parse_indices(args.indices, args.count)
    for index in indices:
        if not (0 <= index < len(files)):
            raise SystemExit(f"audio index out of range: {index} (0..{len(files)-1})")

    print(json.dumps({"listening_dir": str(listening.listening_dir()), "indices": indices}, ensure_ascii=False))
    results: list[dict[str, Any]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        future_map = {pool.submit(build_package, i, files[i], args.force): i for i in indices}
        for fut in concurrent.futures.as_completed(future_map):
            index = future_map[fut]
            try:
                result = fut.result()
            except Exception as exc:  # noqa: BLE001 - batch should report all failures.
                result = {"index": index, "error": str(exc)}
            results.append(result)
            print(json.dumps(result, ensure_ascii=False))

    ok = [r for r in results if not r.get("error")]
    print(json.dumps({"baked": len(ok), "failed": len(results) - len(ok)}, ensure_ascii=False))
    return 0 if len(ok) == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
