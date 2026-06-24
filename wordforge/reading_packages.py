"""Pre-baked reading packages for book-level WordForge reading."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from . import config, corpus


def reading_package_dir() -> Path:
    d = config.data_dir() / "reading_packages"
    d.mkdir(parents=True, exist_ok=True)
    return d


def local_package_dir() -> Path:
    d = reading_package_dir() / "local"
    d.mkdir(parents=True, exist_ok=True)
    return d


def emerson_path() -> Path:
    return reading_package_dir() / "emerson_self_reliance.jsonl"


def audio_path(name: str) -> Path:
    return config.data_dir() / "reading_audio" / name


def audio_exists(name: Any) -> bool:
    return isinstance(name, str) and bool(name) and audio_path(name).exists()


def with_available_audio(package: dict[str, Any]) -> dict[str, Any]:
    """Hide generated audio metadata when the mp3 is not present on this Mac."""
    p = dict(package)
    if p.get("audio_file") and not audio_exists(p.get("audio_file")):
        p.pop("audio_file", None)
        p.pop("audio_duration_ms", None)
        p["segments"] = [
            {k: v for k, v in dict(s).items() if k not in {"start_ms", "end_ms"}}
            for s in p.get("segments", []) or []
        ]
    return p


def package_paths() -> list[Path]:
    paths = sorted(reading_package_dir().glob("*.jsonl"))
    paths.extend(sorted(local_package_dir().glob("*.jsonl")))
    return paths


def _jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as e:
            raise ValueError(f"{path}:{lineno}: invalid JSON: {e}") from e
    return rows


def load_packages() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for path in package_paths():
        for row in _jsonl(path):
            pid = str(row.get("id", ""))
            if not pid or pid in seen:
                continue
            seen.add(pid)
            rows.append(row)
    return rows


def list_packages() -> list[dict[str, Any]]:
    return [
        {
            "id": p.get("id", ""),
            "title": p.get("title", ""),
            "source": p.get("source", ""),
            "route": p.get("route", ""),
            "level": p.get("level", ""),
            "category": p.get("category", "book"),
            "local": bool(p.get("local", False)),
            "has_audio": (
                p.get("audio_index") is not None
                or bool(p.get("audio_url", ""))
                or audio_exists(p.get("audio_file"))
            ),
            "segment_count": len(p.get("segments", []) or []),
            "why_selected": p.get("why_selected", ""),
            "comment_zh": p.get("codex_comment_zh", ""),
        }
        for p in (with_available_audio(p) for p in load_packages())
    ]


def get_package(pid: str) -> dict[str, Any] | None:
    for package in load_packages():
        if package.get("id") == pid:
            return with_available_audio(package)
    return None


def split_sentences(text: str) -> list[str]:
    return [
        s.strip()
        for s in re.split(r"(?<=[.!?])\s+", str(text or "").strip())
        if s.strip()
    ]


def split_scaffold(text: str) -> list[str]:
    return [
        s.strip()
        for s in re.split(r"(?<=[。！？])\s*", str(text or "").strip())
        if s.strip()
    ]


def phrase_hits(sentence: str, palette: list[dict[str, Any]]) -> list[dict[str, Any]]:
    norm = _norm(sentence)
    hits: list[dict[str, Any]] = []
    for item in palette:
        phrase = str(item.get("english", ""))
        if not phrase:
            continue
        pnorm = _norm(phrase)
        tokens = [t for t in pnorm.split() if len(t) > 2]
        if pnorm and (pnorm in norm or (len(tokens) >= 2 and all(t in norm.split() for t in tokens))):
            hits.append(item)
    return hits[:8]


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9'-]+", " ", text.lower())).strip()


COMMENTARY: dict[str, dict[str, Any]] = {
    "emerson-self-reliance-trust-thyself": {
        "codex_comment_zh": "这不是普通的“相信自己”。Emerson 把自我信任写成一种身体会共鸣的内在命令：heart vibrates to that iron string。",
        "codex_comment_en": "The passage converts self-trust from advice into resonance: the heart answers an iron string.",
        "segments": [
            "先抓住命令 spine: Trust thyself. 冒号后面不是解释词义，而是把命令变成图像。",
            "Accept 连续带三个宾语：place, society, connection。它不是消极接受，是先承认你已经站在这里。",
            "Great men have always done so 把个人直觉接到历史维度；done so 指前面的 accept/confide。",
            "The last chain is the hardest: seated / working / predominating. 可信的东西不是外部规则，而是在心里通过手工作。",
        ],
    },
    "emerson-self-reliance-consistency": {
        "codex_comment_zh": "这段在说：不要为了维持昨天的自我形象而背叛今天真实看见的东西。foolish consistency 是对死一致性的讽刺，不是反对诚实。",
        "codex_comment_en": "This is not permission to be sloppy; it is an attack on loyalty to a dead version of yourself.",
        "segments": [
            "A foolish consistency is... 是一句 aphorism：抽象名词 + is + 怪物隐喻，直接下判决。",
            "With consistency 放句首，像中文的“至于一致性”。注意不是 for consistency。",
            "may as well 是 dismissive: 如果你真纠结这种一致性，那你还不如去管墙上的影子。",
            "Speak what you think now... 这里的 hard words 是不把真实想法磨软。",
            "though it contradict... 不是鼓励乱变，是允许今天的真实推翻昨天说过的话。",
        ],
    },
    "emerson-self-reliance-rejected-thoughts": {
        "codex_comment_zh": "这段很适合你：它说被你丢掉的想法，会从陌生人的话里带着陌生的庄严回来。真正的学习不是识别，而是认领。",
        "codex_comment_en": "The important movement is return: your rejected thought comes back with alienated majesty.",
        "segments": [
            "There is a time... 先给出普遍经验：每个人都会发现 jealousy is ignorance。",
            "The eye was placed where one ray should fall... 是强图像：你的视角不是错误，是你的位置。",
            "In every work of genius... 句子很长，但核心是 we recognize our own rejected thoughts。",
            "They come back to us... 注意 alienated majesty：想法因为从别人嘴里回来，所以显得陌生又威严。",
        ],
    },
    "emerson-self-reliance-nonconformist": {
        "codex_comment_zh": "这段是 Self-Reliance 的锋刃：成为一个人，不是先被喜欢，而是不被 conformity 吞掉。",
        "codex_comment_en": "Whoso would be a man must be a nonconformist: the sentence makes manhood a refusal before it is an identity.",
        "segments": [
            "Whoso would be a man 是古典/庄严句式，意思是 whoever wants to be fully human。",
            "must be a nonconformist 把身份定义成动作：不顺从。",
            "Nothing is at last sacred but... 结构是排除法：最后神圣的只剩 integrity of your own mind。",
            "Absolve you to yourself 是宗教/legal 语感：先在自己面前被赦免，才会有世界的认可。",
        ],
    },
}


def build_package_from_passage(passage: dict[str, Any]) -> dict[str, Any]:
    pid = str(passage.get("id", ""))
    comments = COMMENTARY.get(pid, {})
    english = split_sentences(str(passage.get("text_en", "")))
    scaffold = split_scaffold(str(passage.get("scaffold", "")))
    segment_comments = list(comments.get("segments", []) or [])
    segments: list[dict[str, Any]] = []
    for i, sentence in enumerate(english):
        scaffold_text = scaffold[i] if i < len(scaffold) else ""
        comment = segment_comments[i] if i < len(segment_comments) else ""
        segments.append(
            {
                "index": i,
                "text_en": sentence,
                "component_zh": scaffold_text,
                "codex_comment": comment,
                "palette": phrase_hits(sentence, list(passage.get("palette", []) or [])),
            }
        )

    return {
        "id": pid,
        "title": passage.get("title", ""),
        "book": passage.get("book", ""),
        "source": passage.get("source", ""),
        "source_url": passage.get("source_url", ""),
        "route": passage.get("route", passage.get("module", "")),
        "category": "book",
        "local": False,
        "level": passage.get("level", ""),
        "why_selected": passage.get("why_selected", ""),
        "context_note": passage.get("context_note", ""),
        "target_structures": passage.get("target_structures", []),
        "glosses": passage.get("glosses", []),
        "vocab_targets": passage.get("vocab_targets", []),
        "grammar": passage.get("grammar", []),
        "codex_comment_zh": comments.get("codex_comment_zh", ""),
        "codex_comment_en": comments.get("codex_comment_en", ""),
        "segments": segments,
        "text_en": passage.get("text_en", ""),
    }


def bake_emerson_self_reliance() -> dict[str, Any]:
    passages = [
        p
        for p in corpus.load_passages()
        if str(p.get("route", p.get("module", ""))) == "self-reliance"
    ]
    packages = [build_package_from_passage(p) for p in passages]
    out = emerson_path()
    out.write_text(
        "\n".join(json.dumps(p, ensure_ascii=False) for p in packages) + ("\n" if packages else ""),
        encoding="utf-8",
    )
    return {"path": str(out), "count": len(packages), "ids": [p["id"] for p in packages]}
