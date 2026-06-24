#!/usr/bin/env python3
"""Bake the full Project Gutenberg Self-Reliance essay as a Reader package."""

from __future__ import annotations

import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from wordforge import reading_packages  # noqa: E402

SOURCE_URL = "https://www.gutenberg.org/files/2944/2944-0.txt"
OUT = reading_packages.reading_package_dir() / "emerson_self_reliance_full.jsonl"

BLOCKS = [
    {
        "title": "自己的思想就是天才的入口",
        "start_segment": 0,
        "end_segment": 11,
        "core_zh": "爱默生先把天才定义为敢相信并说出自己心中尚未被承认的思想。",
        "why_good_zh": "英文有力量在于用不定式排比、内外反转和审判号角意象，把私人直觉抬升成普遍真理。",
        "watch_zh": [
            "To believe...that is genius 是定义句，前面两个不定式短语都是主语。",
            "Moses, Plato, Milton 不是知识清单，而是反传统权威的例子。",
        ],
        "vocab": [
            {"english": "conventional", "chinese": "因袭的；按惯例的", "usage": "original and not conventional"},
            {"english": "admonition", "chinese": "警醒；劝诫", "usage": "the soul hears an admonition"},
            {"english": "instil", "chinese": "逐渐灌注", "usage": "sentiment they instil"},
            {"english": "latent conviction", "chinese": "潜藏的信念", "usage": "speak your latent conviction"},
            {"english": "set at naught", "chinese": "轻视；置之不理", "usage": "set at naught books and traditions"},
            {"english": "gleam", "chinese": "一闪的光", "usage": "that gleam of light within"},
            {"english": "spontaneous impression", "chinese": "自然涌现的印象", "usage": "abide by spontaneous impression"},
            {"english": "inflexibility", "chinese": "不屈；坚定", "usage": "good-humored inflexibility"},
        ],
    },
    {
        "title": "别人的道路不能替你结果",
        "start_segment": 12,
        "end_segment": 21,
        "core_zh": "他把教育的成熟点说成承认嫉妒无知、模仿自杀，并接受自己被分到的那块土地。",
        "why_good_zh": "英文强在把抽象伦理变成农业、光线、雕刻和神意显现，让自我实现听起来像一种必须完成的自然任务。",
        "watch_zh": [
            "envy is ignorance; imitation is suicide 是两句压缩格言，不是解释型论证。",
            "plot of ground given to him to till 中 till 是耕种，不是 until。",
        ],
        "vocab": [
            {"english": "envy", "chinese": "嫉妒", "usage": "envy is ignorance"},
            {"english": "imitation", "chinese": "模仿", "usage": "imitation is suicide"},
            {"english": "portion", "chinese": "命定的一份；份额", "usage": "take himself as his portion"},
            {"english": "toil", "chinese": "辛劳", "usage": "through his toil"},
            {"english": "till", "chinese": "耕种", "usage": "ground given to him to till"},
            {"english": "manifest", "chinese": "显现出来", "usage": "made manifest by cowards"},
            {"english": "muse", "chinese": "缪斯；灵感", "usage": "no muse befriends"},
            {"english": "deliverance", "chinese": "解脱", "usage": "a deliverance which does not deliver"},
        ],
    },
    {
        "title": "Trust thyself 的核心命令",
        "start_segment": 22,
        "end_segment": 25,
        "core_zh": "Trust thyself 不是自我安慰，而是接受自己的时代、位置和命运，并像承担使命一样行动。",
        "why_good_zh": "一句短促命令后接 iron string，再把个人信任推进到 guides, redeemers, benefactors 的史诗级递进。",
        "watch_zh": [
            "thyself 是古体第二人称，带有圣经和布道语气。",
            "not minors and invalids...but guides... 是否定弱者身份、改认主动角色的平行结构。",
        ],
        "vocab": [
            {"english": "thyself", "chinese": "你自己；古体 self", "usage": "Trust thyself"},
            {"english": "vibrates", "chinese": "共振；颤动", "usage": "heart vibrates to that string"},
            {"english": "providence", "chinese": "天意；神意安排", "usage": "divine providence has found"},
            {"english": "contemporaries", "chinese": "同时代的人", "usage": "society of your contemporaries"},
            {"english": "confided", "chinese": "信托；放心交付", "usage": "confided themselves childlike"},
            {"english": "transcendent", "chinese": "超越性的", "usage": "transcendent destiny"},
            {"english": "minors", "chinese": "未成年人；未成熟者", "usage": "not minors and invalids"},
            {"english": "redeemers", "chinese": "救赎者；拯救者", "usage": "guides, redeemers and benefactors"},
        ],
    },
    {
        "title": "儿童、婴儿和动物的完整眼神",
        "start_segment": 26,
        "end_segment": 38,
        "core_zh": "children, babes, and brutes 被当作未被社会计算撕裂的生命样本，因为他们还敢直接判断。",
        "why_good_zh": "英文用 oracles, unconquered eye, parlor/playhouse 等鲜活比喻，把孩子的无所谓写成一种健康的人性权威。",
        "watch_zh": [
            "brutes 在这里是旧式说法，指动物或未受文明驯化者，不是现代礼貌表达。",
            "pit in the playhouse 指剧场里较吵闹、直接评判的观众区。",
        ],
        "vocab": [
            {"english": "oracles", "chinese": "神谕；启示", "usage": "pretty oracles nature yields"},
            {"english": "brutes", "chinese": "动物；未驯化者", "usage": "children, babes, and brutes"},
            {"english": "arithmetic", "chinese": "计算；算计", "usage": "arithmetic has computed"},
            {"english": "unconquered", "chinese": "未被征服的", "usage": "eye is as yet unconquered"},
            {"english": "prattle", "chinese": "喋喋玩笑；逗弄说话", "usage": "adults who prattle and play"},
            {"english": "piquancy", "chinese": "辛辣魅力；鲜活劲儿", "usage": "its own piquancy and charm"},
            {"english": "nonchalance", "chinese": "若无其事；洒脱", "usage": "nonchalance of boys"},
            {"english": "verdict", "chinese": "判断；裁决", "usage": "gives a genuine verdict"},
        ],
    },
    {
        "title": "成年人被名声关进牢里",
        "start_segment": 39,
        "end_segment": 45,
        "core_zh": "一旦成年人公开行动并被他人记住，他就被自己的公众形象和他人的情感绑住，失去儿童式中立。",
        "why_good_zh": "英文把心理负担写成 jail, Lethe, pledges, darts，抽象的自我意识变成可感的囚禁和攻击。",
        "watch_zh": [
            "éclat 是法语借词，指耀眼声名或轰动效果。",
            "Lethe 是希腊神话中的忘川，表示无法忘掉已经建立的公众身份。",
        ],
        "vocab": [
            {"english": "clapped into jail", "chinese": "被一下关进牢里", "usage": "man is clapped into jail"},
            {"english": "consciousness", "chinese": "自我意识；名声意识", "usage": "by his consciousness"},
            {"english": "éclat", "chinese": "声名；轰动", "usage": "acted or spoken with éclat"},
            {"english": "committed", "chinese": "被绑定立场的", "usage": "a committed person"},
            {"english": "Lethe", "chinese": "忘川", "usage": "There is no Lethe"},
            {"english": "pledges", "chinese": "承诺；既有绑定", "usage": "avoid all pledges"},
            {"english": "unbribable", "chinese": "不可收买的", "usage": "unbiased, unbribable innocence"},
            {"english": "formidable", "chinese": "令人敬畏的；有威力的", "usage": "must always be formidable"},
        ],
    },
    {
        "title": "社会把从众包装成美德",
        "start_segment": 46,
        "end_segment": 54,
        "core_zh": "社会像股份公司一样要求成员交出自由来换安全，而自立恰恰是它最讨厌的东西。",
        "why_good_zh": "英文用 joint-stock company 这种商业隐喻拆穿社会契约，再用短句连击推出 nonconformist 和 integrity。",
        "watch_zh": [
            "Whoso would be a man 是古体倒装感很强的格言句，可理解为 whoever wants to be fully human。",
            "immortal palms 是古典胜利棕榈，不是手掌。",
        ],
        "vocab": [
            {"english": "conspiracy", "chinese": "合谋；阴谋", "usage": "society is in conspiracy"},
            {"english": "joint-stock company", "chinese": "股份公司", "usage": "society is a joint-stock company"},
            {"english": "shareholder", "chinese": "股东", "usage": "each shareholder"},
            {"english": "conformity", "chinese": "从众；顺从", "usage": "virtue in most request"},
            {"english": "aversion", "chinese": "厌恶之物", "usage": "self-reliance is its aversion"},
            {"english": "nonconformist", "chinese": "不从众者", "usage": "must be a nonconformist"},
            {"english": "integrity", "chinese": "完整性；正直", "usage": "integrity of your own mind"},
            {"english": "suffrage", "chinese": "支持；投票认可", "usage": "suffrage of the world"},
        ],
    },
    {
        "title": "从内在活，而不是向好名声投降",
        "start_segment": 55,
        "end_segment": 66,
        "core_zh": "他用极端例子说明，道德名号、宗教传统和公共善意若不来自内在真实，就会变成虚伪。",
        "why_good_zh": "英文力量来自挑衅式对白和反常识反转：Devil, rude truth, love afar, edge，把温和道德话语突然磨出锋刃。",
        "watch_zh": [
            "Abolition 和 Barbadoes 属于19世纪奴隶制废除语境，这段主要攻击表演式慈善，不宜平读成反同情。",
            "thy 是古体 you，增强布道和责问感。",
        ],
        "vocab": [
            {"english": "importune", "chinese": "纠缠劝说；不断催逼", "usage": "importune me with doctrines"},
            {"english": "doctrines", "chinese": "教义；信条", "usage": "doctrines of the church"},
            {"english": "constitution", "chinese": "本性结构；内在构成", "usage": "after my constitution"},
            {"english": "titular", "chinese": "有名无实的", "usage": "everything were titular"},
            {"english": "ephemeral", "chinese": "短暂的", "usage": "titular and ephemeral"},
            {"english": "capitulate", "chinese": "投降；屈服", "usage": "capitulate to badges and names"},
            {"english": "philanthropy", "chinese": "慈善；博爱", "usage": "coat of philanthropy"},
            {"english": "varnish", "chinese": "粉饰；涂饰", "usage": "varnish ambition with tenderness"},
        ],
    },
    {
        "title": "Whim 与我的责任边界",
        "start_segment": 67,
        "end_segment": 74,
        "core_zh": "爱默生故意把内在召唤推到刺耳处：不是所有被社会命名为义务的事都自动属于我。",
        "why_good_zh": "英文以 I shun, Whim, Are they my poor 这些短促第一人称句制造冲击，让责任问题变成现场对抗。",
        "watch_zh": [
            "Whim 字面是任性念头，但这里更像尚不能向外界解释的内在召唤。",
            "lintels of the door-post 带圣经门楣意象，像把个人原则写在门口。",
        ],
        "vocab": [
            {"english": "shun", "chinese": "避开；回避", "usage": "I shun father and mother"},
            {"english": "genius", "chinese": "内在天才；守护灵", "usage": "when my genius calls"},
            {"english": "lintels", "chinese": "门楣", "usage": "lintels of the door-post"},
            {"english": "whim", "chinese": "一时念头；任性冲动", "usage": "write Whim"},
            {"english": "show cause", "chinese": "说明理由", "usage": "show cause why I seek"},
            {"english": "obligation", "chinese": "义务", "usage": "obligation to put poor men"},
            {"english": "grudge", "chinese": "吝惜；不情愿给", "usage": "grudge the dollar"},
            {"english": "affinity", "chinese": "亲缘；精神相契", "usage": "spiritual affinity"},
        ],
    },
    {
        "title": "生命不是给人观看的功德表",
        "start_segment": 75,
        "end_segment": 91,
        "core_zh": "他反对用零散善行来赎买一种没有活出来的生命，主张只关心自己必须做的事。",
        "why_good_zh": "英文反复对照 actions 与 life, spectacle 与 genuine, world 与 solitude，把道德评价从外部成绩单拉回生命整体。",
        "watch_zh": [
            "forbear 是 refrain from doing，指不做某事，不是忍耐别人。",
            "the great man...in the midst of the crowd...independence of solitude 是全段平衡句核心。",
        ],
        "vocab": [
            {"english": "expiation", "chinese": "赎罪；补偿罪过", "usage": "pay a fine in expiation"},
            {"english": "penances", "chinese": "苦修；赎罪行为", "usage": "virtues are penances"},
            {"english": "spectacle", "chinese": "供人观看的景观", "usage": "not for a spectacle"},
            {"english": "strain", "chinese": "格调；品质层次", "usage": "lower strain but genuine"},
            {"english": "genuine", "chinese": "真实的；出自本心的", "usage": "so it be genuine"},
            {"english": "forbear", "chinese": "克制不做", "usage": "do or forbear actions"},
            {"english": "intrinsic right", "chinese": "内在权利", "usage": "where I have intrinsic right"},
            {"english": "arduous", "chinese": "艰难的", "usage": "equally arduous rule"},
        ],
    },
    {
        "title": "通往 foolish consistency 的前奏",
        "start_segment": 92,
        "end_segment": 126,
        "core_zh": "在名句之前，爱默生先说从众会分散力量、固定身份会遮蔽真实的人，而害怕违背过去的自己正是自信的另一种敌人。",
        "why_good_zh": "英文把一致性恐惧写成 screens, blindman's-buff, prison-uniform, corpse of your memory, thousand-eyed present，层层把抽象束缚变成身体和视觉压力。",
        "watch_zh": [
            "这里的 consistency 不是逻辑一致性，而是死守过去人设、怕让旁观者失望。",
            "Joseph his coat 是《创世记》约瑟逃离诱惑的典故，意思是丢下理论赶快逃向当下真实。",
        ],
        "vocab": [
            {"english": "usages", "chinese": "习俗；惯例做法", "usage": "conforming to usages"},
            {"english": "scatters your force", "chinese": "分散你的力量", "usage": "it scatters your force"},
            {"english": "blindman's-buff", "chinese": "蒙眼捉人游戏", "usage": "game of conformity"},
            {"english": "sect", "chinese": "宗派；派别", "usage": "If I know your sect"},
            {"english": "retained attorney", "chinese": "受雇律师", "usage": "He is a retained attorney"},
            {"english": "askance", "chinese": "斜眼看；怀疑地看", "usage": "look askance on him"},
            {"english": "orbit", "chinese": "轨道；行动轨迹", "usage": "computing our orbit"},
            {"english": "thousand-eyed present", "chinese": "千眼般的当下", "usage": "bring the past into the present"},
        ],
    },
    {
        "title": "foolish consistency：死一致性的怪物",
        "start_segment": 127,
        "end_segment": 132,
        "core_zh": "他终于点名：真正可怕的不是被误解，而是为了让自己看起来一致而背叛今天真实看见的东西。",
        "why_good_zh": "hobgoblin 把抽象一致性变成吓小心灵的小怪物，little statesmen/philosophers/divines 连击讽刺各种小权威。",
        "watch_zh": [
            "hard words 不是难词，而是不把真实想法磨软的强硬说法。",
            "To be great is to be misunderstood 是全段最硬的格言，不是受害者安慰。",
        ],
        "vocab": [
            {"english": "foolish consistency", "chinese": "愚蠢的一致性；死守昨日自我", "usage": "A foolish consistency is..."},
            {"english": "hobgoblin", "chinese": "吓人的小妖怪；心魔", "usage": "hobgoblin of little minds"},
            {"english": "adored by", "chinese": "被……崇拜", "usage": "adored by little statesmen"},
            {"english": "may as well", "chinese": "也完全可以；还不如", "usage": "may as well concern himself"},
            {"english": "hard words", "chinese": "强硬的话；不磨软的话", "usage": "speak in hard words"},
            {"english": "contradict", "chinese": "与……矛盾", "usage": "contradict everything you said"},
            {"english": "misunderstood", "chinese": "被误解", "usage": "To be great is to be misunderstood"},
            {"english": "took flesh", "chinese": "化为肉身；成为人", "usage": "spirit that ever took flesh"},
        ],
    },
]


def _download() -> str:
    with urllib.request.urlopen(SOURCE_URL, timeout=30) as r:
        return r.read().decode("utf-8-sig", errors="replace").replace("\r\n", "\n")


def _extract_self_reliance(book: str) -> str:
    starts = [m.start() for m in re.finditer(r"(?m)^SELF-RELIANCE$", book)]
    if len(starts) < 2:
        raise ValueError("could not find the body SELF-RELIANCE heading")
    start = starts[1]
    end_match = re.search(r"(?m)^III\.\nCOMPENSATION$", book[start:])
    if not end_match:
        raise ValueError("could not find the next essay heading")
    essay = book[start : start + end_match.start()]
    essay = re.sub(r"(?m)^SELF-RELIANCE\s*", "", essay, count=1)
    essay = re.sub(r"\n{3,}", "\n\n", essay).strip()
    return essay


def _sentences(text: str) -> list[str]:
    flat = re.sub(r"\s+", " ", text).strip()
    pieces = re.split(r"(?<=[.!?])\s+(?=[“\"A-Z])", flat)
    return [p.strip() for p in pieces if p.strip()]


def main() -> int:
    essay = _extract_self_reliance(_download())
    segments = [
        {
            "index": i,
            "text_en": sentence,
            "component_zh": "",
            "codex_comment": "",
            "palette": [],
        }
        for i, sentence in enumerate(_sentences(essay))
    ]
    package = {
        "id": "emerson-self-reliance-complete",
        "title": "Self-Reliance · Complete Essay",
        "book": "Emerson · Essays, First Series",
        "source": "Ralph Waldo Emerson, Essays: First Series, Self-Reliance (Project Gutenberg #2944)",
        "source_url": "https://www.gutenberg.org/ebooks/2944",
        "route": "self-reliance",
        "category": "book",
        "local": False,
        "level": "C1-C2",
        "why_selected": "The complete public-domain essay behind the shorter practice excerpts, for continuous reading and listening.",
        "context_note": "Fast-baked full text: audio and sentence map first; sentence-by-sentence Chinese scaffolds can be added later for the parts you choose to study closely.",
        "target_structures": ["aphorism", "imperative", "parallelism", "abstract noun chains", "long periodic sentences"],
        "glosses": [
            {"word": "self-reliance", "hint": "trust in one's own perception and responsibility", "chinese": "自立；自信；依靠自己的判断"},
            {"word": "conformity", "hint": "living by social pattern rather than inner perception", "chinese": "从众；顺从"},
            {"word": "integrity", "hint": "inner wholeness; not splitting oneself for approval", "chinese": "完整性；正直"},
            {"word": "consistency", "hint": "keeping the same public self even when today's perception changes", "chinese": "一致性"},
        ],
        "vocab_targets": ["self-reliance", "conformity", "integrity", "consistency", "intuition", "genius"],
        "grammar": [
            "Emerson often states an aphorism, then expands it through metaphor and command.",
            "Many sentences are long because appositions, participles, and parallel phrases keep attaching to one main claim.",
            "Archaic or formal diction gives the essay a sermon-like pressure.",
        ],
        "codex_comment_zh": "这是完整正文包：先让你今晚能听完、滚动读完、随时选句提问；精细中文脚手架可以从你卡住的句子开始补。",
        "codex_comment_en": "Complete text package: continuous listening first, close reading on demand sentence by sentence.",
        "blocks": BLOCKS,
        "segments": segments,
        "text_en": essay,
    }
    OUT.write_text(json.dumps(package, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"path": str(OUT), "chars": len(essay), "segments": len(segments)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
