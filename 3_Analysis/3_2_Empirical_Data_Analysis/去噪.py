# ============================================================
# 病历规则去噪及完整病历导出
#
# 输入：
# DATA/Complains_clean_step1_to_step4.xlsx
#   工作表：Clean_data
#
# 输出：
# OUTPUT/Complains_denoised.xlsx
#   Clean_data：去噪后的完整病历
#   规则命中：按删除内容去重后的汇总
#   删除明细：每次删除的位置、内容和上下文
#   统计：按处理类型、规则汇总
#
# 处理顺序：
# 1. 清理明确标记的心理测验结果段。
# 2. 应用原有完整片段去噪规则。
# 3. 删除残留的明确量表分数。
# 4. 单独删除剩余文本中的药名。
#
# 原文及其他患者字段保留。
# 去噪后为空的病历保留并标记，交由下一步R处理。
# ============================================================

from pathlib import Path
from functools import lru_cache
import re
import unicodedata

import pandas as pd


# ==================== 1. 路径 ====================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "DATA"
OUTPUT_DIR = BASE_DIR / "OUTPUT"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

INPUT_FILE = DATA_DIR / "Complains_clean_step1_to_step4.xlsx"
RESULT_FILE = OUTPUT_DIR / "Complains_denoised.xlsx"

ID_COL = "门诊ID"
TEXT_COL = "现病史"


# ==================== 2. 基础表达 ====================

def spaced_names(names):
    """允许名称内部存在空格；长名称优先。"""
    return "(?:" + "|".join(
        r"[ \t]*".join(re.escape(char) for char in name)
        for name in sorted(set(names), key=len, reverse=True)
    ) + ")"


NUM = r"(?:\d+(?:\.\d+)?|[一二三四五六七八九十百两半]+)"
INT = r"(?:\d{1,2}|[一二三四五六七八九十两]+)"

DURATION = (
    rf"{NUM}(?:[-—~至到]{NUM})?"
    r"(?:个)?(?:年|月|周|星期|天|日)(?:余|多|左右)?"
)

TIME = (
    rf"(?:(?:近|最近|过去|已有|已)?{DURATION}(?:前|后|以来)?"
    r"|既往|曾经|此前|之前|目前|现在|近期|近日|今日|今天)"
)

DATE = r"\d{2,4}[-./年]\d{1,2}(?:[-./月]\d{1,2}日?|月)?"

AGE = (
    rf"{INT}(?:[-—~至到]{INT})?岁"
    rf"(?:半|{INT}(?:个)?月)?"
    rf"(?:{INT}(?:天|日))?"
)

GRADE = (
    r"(?:(?:小学|初中|高中|中学)?"
    r"(?:[一二三四五六七八九十]{1,3}|\d{1,2})年级"
    r"|初[一二三123]|高[一二三123])"
)

FAMILY = (
    r"(?:爸爸|妈妈|父亲|母亲|父母|家长"
    r"|奶奶|爷爷|外婆|外公|祖母|祖父|父|母)"
)

FAMILY_GROUP = rf"{FAMILY}(?:(?:和|及|与|、)?{FAMILY})*"


# ==================== 3. 药名及原有用药规则 ====================

# 原有药名，加上本次病历中明确出现的四种药名。
# 后续发现其他药名，可直接补入此列表。
DRUG_NAMES = [
    "硫必利",
    "安坦",
    "舍曲林",
    "择思达",
    "菖麻熄风片",
    "草酸艾司西酞普兰",
    "艾司西酞普兰",
    "奥沙西泮",
    "布洛芬",
    "阿立哌唑",
    "氟西汀",
    "喹硫平",
    "奥氮平",
    "劳拉西泮",
]

# 仅在后面确实跟着清单内药名时，连同这些名称前缀删除。
DRUG_PREFIX = (
    r"(?:(?:盐酸|草酸|富马酸|氢溴酸|马来酸)[ \t]*)?"
)

DRUG = DRUG_PREFIX + spaced_names(DRUG_NAMES)
DRUG_PATTERN = re.compile(DRUG, re.IGNORECASE)

DOSE = (
    rf"{NUM}(?:/{NUM})?"
    r"(?:mg|ml|g|毫克|毫升|克|片|粒|滴|支|袋)"
)

FREQUENCY = (
    rf"(?:{NUM}次(?:/(?:d|日|天))?"
    r"|每天|每日|一天|一日|每晚|早晚"
    r"|早|中|午|晚|睡前|饭前|饭后"
    r"|qd|bid|tid|qid|qn|po)"
)

MED_PREFIX = rf"(?:{TIME})?(?:曾经|曾|间断|长期|持续)*"

# 沿用：只有整段都是简单用药记录时，才整段删除。
MED_NAMED = (
    MED_PREFIX
    + r"(?:服用|口服|使用|用|予|给予|加用|合并)?"
    + DRUG
    + r"(?:口服溶液|口服液|胶囊|片)?"
    + rf"(?:{DOSE}|{FREQUENCY}|{DURATION}"
      r"|治疗|服用|口服|[()、,;])*"
)

MED_HISTORY = (
    MED_PREFIX
    + r"(?:"
      r"停药|自行停药|停服药物|停用药物|服药|用药"
      r"|(?:未|未曾|没有)(?:长期|持续)?"
      r"(?:服用|服|使用|用)(?:任何)?药(?:物)?"
      r"|无特殊处理"
      r")"
    + rf"(?:{DURATION})?"
)

MED_SHORT = r"(?:qd|bid|tid|qid|qn|po)治疗"


# ==================== 4. 心理测验结果段 ====================

# 不包含精神检查、精神状态检查等标题。
ASSESSMENT_HEADERS = [
    "心理检查结果", "心理检查",
    "心理测试结果", "心理测试",
    "心理测验结果", "心理测验",
    "心理测评结果", "心理测评",
    "心理评估结果", "心理评估",
    "测评结果", "评估结果",
    "脑电生物点反馈", "脑电生物电反馈",
    "沙盘结果", "沙盘总结", "沙盘",
    "韦氏智力测评", "瑞文智力测评", "智力测评",
    "症状自评量表", "症状自评",
    "儿童行为量表", "注意力评估量表",
    "注意力诊断量表", "困难量表", "压力测评",
]

NEXT_HEADERS = ASSESSMENT_HEADERS + [
    "陪诊人", "主诉", "现病史",
    "既往史", "过敏史", "流行病学史", "个人史", "家族史",
    "体格检查", "专科查体", "专科检查", "辅助检查",
    "精神检查结果", "精神状态检查", "精神科检查", "精神检查",
    "诊断", "诊疗计划",
    "表格<诊断>内容", "表格<处置>内容",
    "医师签名", "就诊日期", "日期",
]

ASSESSMENT_TITLE = spaced_names(ASSESSMENT_HEADERS)
NEXT_TITLE = spaced_names(NEXT_HEADERS)

ASSESSMENT_LEAD = (
    r"(?:(?:当地|本院|外院)[ \t]*"
    r"|(?:在|于)?[ \t]*"
    r"[\u4e00-\u9fffA-Za-z0-9]{2,20}"
    r"(?:医院|中心|门诊|诊所)[ \t]*[:：]?[ \t]*)?"
)

# 删除范围：
# 从明确心理测验标记开始，
# 到句末标点、分号、换行或下一个明确栏目结束。
# 逗号和顿号不作为结束位置。
ASSESSMENT_RESULT_PATTERN = re.compile(
    rf"(?:^|(?<=[，,。；;！？!?\r\n]))[ \t]*"
    rf"(?P<body>{ASSESSMENT_LEAD}{ASSESSMENT_TITLE}"
    r"[ \t]*(?:结果[ \t]*)?"
    r"(?:[:：]|(?:显示|提示|表明|发现|为)[ \t]*[:：]?)"
    r"[ \t]*[^。；;！？!?\r\n]*?)"
    rf"(?=[，,]?[ \t]*{NEXT_TITLE}[ \t]*[:：]"
    r"|[。；;！？!?\r\n]|$)",
    re.IGNORECASE,
)


# ==================== 5. 明确量表分数 ====================

# AS仅在后接评分、得分、冒号等标记时识别，
# 不把普通英文中的as直接当成量表名称。
SCALE = (
    r"(?:SNAP(?:[-－ ]?(?:IV|4))?|CPT"
    r"|SDS|SAS|CDI|DSRSC|SCARED"
    r"|PHQ(?:[-－ ]?9)?|DASS(?:[-－ ]?21)?"
    r"|HAMD(?:[-－ ]?\d+)?|HAMA(?:[-－ ]?\d+)?"
    r"|SCL[-－ ]?90|Conners|CBCL|SDQ"
    r"|汉密尔顿(?:抑郁|焦虑)?(?:量表)?"
    r"|症状自评(?:量表)?|儿童行为量表"
    r"|注意力评估量表|注意力诊断量表"
    r"|困难量表|压力测评|自我意识"
    r"|AS(?=[ \t]*(?:评分|总分|得分|分数|[:：=])))"
)

SCORE_VALUE = (
    r"(?:"
    r"[+\-]?\d+(?:[.．]\d+)?"
    r"(?:[ \t]*[-－/][ \t]*\d+(?:[.．]\d+)?)*"
    r"(?![\d.．])"
    r"(?![ \t]*(?:分钟|分后|分前|小时|天|周|月|年|岁|次))"
    r"[ \t]*分?"
    r"|[+＋\-－±](?!\d)"
    r")"
)

SCALE_SCORE_CORE = (
    rf"{SCALE}"
    r"[ \t]*(?:量表|问卷|测验)?"
    r"[ \t]*(?:总分|评分|得分|分数|结果)?"
    r"[ \t]*(?:为)?[ \t]*[:：=]?[ \t]*"
    + SCORE_VALUE
)

# 原有整片段量表结果规则，补齐“评分／得分”等写法。
SCALE_RESULT = (
    r"(?:[\u4e00-\u9fff]{2,20}医院)?"
    + SCALE_SCORE_CORE
)

# 局部删除时，优先连同只包裹该分数的括号一起删除。
PAREN_SCALE_SCORE_PATTERN = re.compile(
    rf"[（(][ \t]*{SCALE_SCORE_CORE}[ \t]*[)）]",
    re.IGNORECASE,
)

INLINE_SCALE_SCORE_PATTERN = re.compile(
    rf"(?<![A-Za-z0-9]){SCALE_SCORE_CORE}",
    re.IGNORECASE,
)

DIMENSION = (
    r"(?:躯体化|强迫|人际关系敏感|抑郁|焦虑"
    r"|敌对|恐怖|偏执|精神病性)"
)

MULTIPLE_SCORES = (
    rf"(?:{DIMENSION}[:=]?\d+(?:\.\d+)?分?[-—、,;])+"
    r"(?:所有|各项)分数(?:值)?均高于正常"
)


# ==================== 6. 原有就诊、背景及检查规则 ====================

VISIT_PLACES = [
    "本院", "外院", "当地", "医院", "门诊", "我院", "我科",
    "玉田", "山东济南", "复旦儿科", "京都儿童医院",
]

PLACE = "(?:" + "|".join(
    re.escape(place)
    for place in sorted(VISIT_PLACES, key=len, reverse=True)
) + ")"

VISIT = (
    rf"(?:建议|嘱|预约|计划)?(?:{TIME})?"
    r"(?:先后|曾|再次)?(?:到|去|来|回|在|于|至)?"
    rf"(?:{PLACE}(?:[、,及和]{PLACE})*(?:等)?)?"
    r"(?:就诊|复诊|复查|随诊|来诊)"
)

VISIT_FIXED = (
    r"(?:(?:患儿|患者|孩子)?(?:主动)?(?:要求|请求)就诊"
    r"|开(?:具)?(?:诊断|病假)证明"
    r"|今日来诊|今日复诊|今日就诊|追问既往)"
)

ACCOMPANY = (
    rf"(?:陪诊人:)?(?:患儿|患者|孩子)?(?:由)?"
    rf"(?:{GRADE})?{FAMILY_GROUP}"
    r"(?:陪伴|陪诊|伴诊|带来|带)"
    r"(?:就诊|来诊|来院|复诊)?"
)

AGE_LABEL = (
    rf"(?:患儿|患者|孩子|年龄:?|现年|今年)"
    rf"(?:现年|今年)?{AGE}"
)

GRADE_LABEL = (
    r"(?:现在|目前|现)?"
    r"(?:就读于|就读|上|读|升入|升)?"
    + GRADE
    + r"(?:上学期|下学期|毕业)?"
)

DEVELOPMENT_ACTION = (
    r"(?:会走路|会说话|会走)"
    r"(?:(?:和|及|、)?(?:会走路|会说话|会走))*"
)

DEVELOPMENT = (
    rf"(?:患儿|患者|孩子)?(?:于|在)?{AGE}"
    r"(?:时|左右|开始)?"
    rf"(?:{DEVELOPMENT_ACTION}"
    r"|(?:上|入)?幼儿园(?:小班|中班|大班)?"
    r"|入园|入托|入学)"
)

CAREGIVER = rf"(?:{FAMILY}|老人)"
CAREGIVER_GROUP = (
    rf"{CAREGIVER}(?:(?:和|及|与|、)?{CAREGIVER})*"
)

EARLY_CARE = (
    rf"(?:患儿|患者|孩子)?"
    rf"(?:{AGE}|从小|自幼|出生后|生后)"
    r"(?:时|起|开始)?(?:由|主要由)?"
    + CAREGIVER_GROUP
    + r"(?:带大|带|抚养|照顾|照料)"
      r"(?:孩子|患儿|患者)?"
)

DELIVERY = r"(?:顺产|自然分娩|剖宫产|剖腹产)"

BIRTH = (
    rf"(?:第{INT}胎第{INT}产"
    rf"(?:(?:足月)?{DELIVERY})?"
    rf"|足月{DELIVERY}|{DELIVERY})"
)

EXAM = (
    r"(?:(?:头颅|头部|脑|全腹部|腹部)?"
    r"(?:CT|MRI|核磁(?:共振)?)(?:检查)?"
    r"|(?:脑电图|心电图|血常规)(?:检查)?"
    r"|检查评估|(?:各项|相关|辅助)?检查)"
)

EXAM_RESULT = (
    rf"(?:{TIME}|{DATE})?"
    r"(?:院外|外院|本院|当地|感染科)?"
    r"(?:复查|检查|查|行|做)?"
    rf"{EXAM}(?:[、,及和]{EXAM})*"
    r":?(?:未见(?:明显)?异常|无(?:明显)?异常"
    r"|基本正常|正常|异常|提示异常)"
)

MEASUREMENT = (
    rf"(?:{TIME}|{DATE})?(?:复查|检查)?"
    r"[+\-]?\d+(?:\.\d+)?(?:/\d+(?:\.\d+)?)?"
    r"(?:bpm|次/分|IU/ml|U/L|mmol/L|mmHg|℃|°C|cm|kg)"
)

ADMIN_DATE = (
    rf"(?:就诊日期|记录日期|日期):{DATE}"
    r"(?:\d{1,2}:\d{2}(?::\d{2})?)?"
)

SERIAL = r"\d{1,3}(?:\.\d{1,3}){0,2}\)"

EMPTY_TEMPLATE = (
    r"(?:医师签名|医生签名|表格<(?:诊断|处置)>内容):?"
)


# ==================== 7. 已确认的精神检查固定表述 ====================

MENTAL_PHRASES = [
    "神清", "神志清", "神志清楚", "神志清晰", "神志清醒",
    "意识清", "意识清楚", "意识清晰", "意识清醒",
    "意识状态清楚", "意识状态清晰", "意识状态清醒",
    "定向完整", "定向正常",
    "定向力完整", "定向力正常", "定向力良好",
    "时间定向完整", "地点定向完整", "人物定向完整",
    "检查合作", "检查配合", "配合检查",
    "仪表整洁", "衣着整洁", "步入诊室", "安坐",
    "接触被动",
]

MENTAL_ITEM = "|".join(
    re.escape(text)
    for text in sorted(MENTAL_PHRASES, key=len, reverse=True)
)

MENTAL_FIXED = (
    r"(?:患儿|患者)?"
    r"(?:目前|现|检查时|查体时)?"
    rf"(?:{MENTAL_ITEM})"
    rf"(?:[、:]?(?:{MENTAL_ITEM}))*"
)


# ==================== 8. 完整片段规则 ====================

RULES = [
    ("独立药名及用药经过", MED_NAMED),
    ("服药停药记录", MED_HISTORY),
    ("用药缩写", MED_SHORT),
    ("就诊复查经过", VISIT),
    ("就诊及问诊套话", VISIT_FIXED),
    ("陪诊记录", ACCOMPANY),
    ("年龄标签", AGE_LABEL),
    ("学段年级标签", GRADE_LABEL),
    ("发育及入园经历", DEVELOPMENT),
    ("早期照料经历", EARLY_CARE),
    ("出生背景", BIRTH),
    ("量表测验结果", SCALE_RESULT),
    ("独立量表名称", SCALE),
    ("多项量表分数", MULTIPLE_SCORES),
    ("辅助检查结果", EXAM_RESULT),
    ("独立测量数值", MEASUREMENT),
    ("精神检查固定表述", MENTAL_FIXED),
    ("行政日期字段", ADMIN_DATE),
    ("序号残留", SERIAL),
    ("空白模板", EMPTY_TEMPLATE),
]

RULES = [
    (name, re.compile(pattern, re.IGNORECASE))
    for name, pattern in RULES
]


def clean_fragment(text):
    return re.sub(r"\s+", " ", text).strip(" 、：:")


@lru_cache(maxsize=None)
def match_rule(sentence):
    text = unicodedata.normalize("NFKC", sentence)
    text = re.sub(r"\s+", "", text).strip(",。;:、")

    for name, pattern in RULES:
        if pattern.fullmatch(text):
            return name

    return "未命中"


# ==================== 9. 切片及标点整理 ====================

FRAGMENT_PATTERN = re.compile(r"[^。！？!?；;，,\r\n]+")
LIST_FRAGMENT_PATTERN = re.compile(r"[^、]+")


def iter_fragments(note):
    # 先匹配完整分句。
    # 整句不能删除时，再按顿号细分。
    for match in FRAGMENT_PATTERN.finditer(note):
        raw_fragment = match.group()
        sentence = clean_fragment(raw_fragment)

        if not sentence:
            continue

        if (
            "、" in raw_fragment
            and match_rule(sentence) == "未命中"
        ):
            for part in LIST_FRAGMENT_PATTERN.finditer(raw_fragment):
                yield (
                    match.start() + part.start(),
                    match.start() + part.end(),
                    part.group(),
                )
        else:
            yield match.start(), match.end(), raw_fragment


SEPARATOR_RUN = re.compile(
    r"[。！？!?；;，,、\r\n]"
    r"(?:[ \t]*[。！？!?；;，,、\r\n])+"
)

SEPARATOR_PRIORITY = {
    "、": 1,
    ",": 2, "，": 2,
    ";": 3, "；": 3,
    "\r": 4, "\n": 4,
    "。": 5, "！": 5, "？": 5, "!": 5, "?": 5,
}


def tidy_text(text):
    # 清理删除后形成的空括号。
    text = re.sub(r"[（(][ \t]*[)）]", "", text)

    # 合并相邻分隔符，保留句子边界。
    text = SEPARATOR_RUN.sub(
        lambda match: max(
            match.group(),
            key=lambda char: SEPARATOR_PRIORITY.get(char, 0),
        ),
        text,
    )

    return (
        text.lstrip(" \t\r\n，,。；;、！？!?")
        .rstrip(" \t\r\n，,；;、")
    )


# ==================== 10. 保留原文位置的删除方法 ====================

def mask_spans(text, spans):
    """
    仅在匹配用的副本中，用等长换行遮住已删除内容。
    字符位置不变，后续规则不会重复匹配这些内容。
    最终输出仍根据原文和删除位置生成。
    """
    parts = []
    cursor = 0

    for start, end in sorted(spans):
        parts.append(text[cursor:start])
        parts.append("\n" * (end - start))
        cursor = end

    parts.append(text[cursor:])
    return "".join(parts)


def mask_matches(text, pattern, edits, kind, rule, group=0):
    spans = []

    for match in pattern.finditer(text):
        start, end = match.span(group)
        spans.append((start, end))
        edits.append((start, end, kind, rule))

    return mask_spans(text, spans)


def denoise_note(note):
    edits = []

    # 1. 明确标记的心理测验结果段。
    working = mask_matches(
        note,
        ASSESSMENT_RESULT_PATTERN,
        edits,
        kind="整段删除",
        rule="心理测验结果段",
        group="body",
    )

    # 2. 原有完整片段规则。
    fragment_spans = []

    for start, end, raw_fragment in iter_fragments(working):
        sentence = clean_fragment(raw_fragment)

        if not sentence:
            continue

        rule = match_rule(sentence)

        if rule != "未命中":
            fragment_spans.append((start, end))
            edits.append((start, end, "整段删除", rule))

    working = mask_spans(working, fragment_spans)

    # 3. 剩余文本中的明确量表分数。
    working = mask_matches(
        working,
        PAREN_SCALE_SCORE_PATTERN,
        edits,
        kind="分数删除",
        rule="括号内量表分数",
    )

    working = mask_matches(
        working,
        INLINE_SCALE_SCORE_PATTERN,
        edits,
        kind="分数删除",
        rule="行内量表分数",
    )

    # 4. 剩余文本中的药名，仅删除名称。
    mask_matches(
        working,
        DRUG_PATTERN,
        edits,
        kind="药名删除",
        rule="药名局部删除",
    )

    # 各阶段匹配时已遮住此前删除的位置，
    # 因而这些删除区间互不重叠。
    edits.sort(key=lambda item: item[0])

    kept_parts = []
    cursor = 0

    for start, end, _, _ in edits:
        kept_parts.append(note[cursor:start])
        cursor = end

    kept_parts.append(note[cursor:])
    cleaned = "".join(kept_parts)

    if edits:
        cleaned = tidy_text(cleaned)

    return cleaned, edits


# ==================== 11. 读取并处理完整病历 ====================

df = pd.read_excel(
    INPUT_FILE,
    sheet_name="Clean_data",
    dtype={ID_COL: str},
)

df["现病史_去噪前"] = df[TEXT_COL].fillna("").astype(str)

cleaned_notes = []
fragment_counts = []
score_counts = []
drug_counts = []
deleted_rows = []

for row_index, row in df.iterrows():
    note = row["现病史_去噪前"]
    cleaned, edits = denoise_note(note)

    cleaned_notes.append(cleaned)

    # 检查结果段和原有完整片段，记入“删除片段数”。
    fragment_counts.append(
        sum(kind == "整段删除" for _, _, kind, _ in edits)
    )

    # 仅统计局部删除；不重复统计随整段删除的分数和药名。
    score_counts.append(
        sum(kind == "分数删除" for _, _, kind, _ in edits)
    )

    drug_counts.append(
        sum(kind == "药名删除" for _, _, kind, _ in edits)
    )

    for operation_no, (start, end, kind, rule) in enumerate(
        edits,
        start=1,
    ):
        deleted_rows.append({
            "门诊ID": row[ID_COL],
            "原表行号": row_index + 2,
            "操作序号": operation_no,
            "处理类型": kind,
            "命中规则": rule,
            "起始位置": start,
            "结束位置": end,
            "删除内容": note[start:end],
            "删除字符数": end - start,
            "上下文": (
                note[max(0, start - 40):start]
                + "【" + note[start:end] + "】"
                + note[end:end + 40]
            ),
        })

df[TEXT_COL] = cleaned_notes
df["删除片段数"] = fragment_counts
df["删除分数次数"] = score_counts
df["删除药名次数"] = drug_counts
df["去噪后为空"] = df[TEXT_COL].str.strip().eq("")


# ==================== 12. 删除明细及统计 ====================

# 位置均对应“现病史_去噪前”：
# 起始位置从0计数，结束位置不包含在删除范围内。
deleted = pd.DataFrame(
    deleted_rows,
    columns=[
        "门诊ID",
        "原表行号",
        "操作序号",
        "处理类型",
        "命中规则",
        "起始位置",
        "结束位置",
        "删除内容",
        "删除字符数",
        "上下文",
    ],
)

matched = (
    deleted.groupby(
        ["处理类型", "命中规则", "删除内容"],
        sort=False,
    )
    .agg(
        出现次数=("门诊ID", "size"),
        涉及病历数=("门诊ID", "nunique"),
    )
    .reset_index()
    .sort_values(
        ["处理类型", "命中规则", "出现次数"],
        ascending=[True, True, False],
    )
)

# 整段、分数和药名分开统计，避免混用片段数与药名次数。
summary = (
    deleted.groupby(
        ["处理类型", "命中规则"],
        sort=False,
    )
    .agg(
        删除次数=("删除内容", "size"),
        不同删除内容数=("删除内容", "nunique"),
        涉及病历数=("门诊ID", "nunique"),
        删除字符数=("删除字符数", "sum"),
    )
    .reset_index()
)


# ==================== 13. 导出 ====================

with pd.ExcelWriter(RESULT_FILE, engine="openpyxl") as writer:
    df.to_excel(
        writer,
        sheet_name="Clean_data",
        index=False,
    )

    matched.to_excel(
        writer,
        sheet_name="规则命中",
        index=False,
    )

    deleted.to_excel(
        writer,
        sheet_name="删除明细",
        index=False,
    )

    summary.to_excel(
        writer,
        sheet_name="统计",
        index=False,
    )

affected_notes = int(
    df[["删除片段数", "删除分数次数", "删除药名次数"]]
    .sum(axis=1)
    .gt(0)
    .sum()
)

print(f"输入病历：{len(df):,} 份")
print(f"整段删除：{sum(fragment_counts):,} 次")
print(f"局部分数删除：{sum(score_counts):,} 次")
print(f"局部药名删除：{sum(drug_counts):,} 次")
print(f"发生去噪的病历：{affected_notes:,} 份")
print(f"去噪后为空：{int(df['去噪后为空'].sum()):,} 份")
print(f"结果已保存：{RESULT_FILE}")