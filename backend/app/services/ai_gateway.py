"""AI 网关:Gemini 调用封装。

- 未配置 GEMINI_API_KEY 时所有函数返回 None,业务方优雅降级;
- 验资视频先经 ffmpeg 抽关键帧,再以图片送模型识别;
- 所有调用失败不抛异常,返回 None(功能降级,不影响主流程)。
"""
import base64
import json
import subprocess
import tempfile
import urllib.request
from pathlib import Path

from ..config import settings

def _gemini_url() -> str:
    base = (settings.gemini_api_base or "https://generativelanguage.googleapis.com").rstrip("/")
    return f"{base}/v1beta/models/{settings.gemini_model}:generateContent"


def ai_enabled() -> bool:
    return bool(settings.gemini_api_key)


def _call(parts: list[dict]) -> str | None:
    if not ai_enabled():
        return None
    body = json.dumps({"contents": [{"parts": parts}]}).encode("utf-8")
    req = urllib.request.Request(
        _gemini_url() + f"?key={settings.gemini_api_key}",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        return None


def extract_publication_fields(text: str) -> dict | None:
    """自然语言发布 → 结构化字段"""
    prompt = (
        "你是供应链撮合系统的信息抽取助手。从下面的自然语言描述中抽取供需信息,"
        "只输出 JSON,不要任何其他文字。字段:type(demand=采购需求/supply=供货信息)、"
        "title(标题)、product_name(产品型号,如 B300)、quantity(数量,保留原样字符串)、"
        "price_min(最低价,数字,人民币元,无则 null)、price_max(最高价,无则 null)、"
        "currency(CNY/USD/HKD)、intent_modes(数组,取值:预付款/信用证-国内/信用证-跨境,无则[])、"
        "goods_preference(现货/准现货/期货,无则空串)、content(规范化后的完整描述)。"
        "金额单位:若描述为'万',换算为元(如 142万 = 1420000)。\n\n描述:\n" + text
    )
    out = _call([{"text": prompt}])
    if not out:
        return None
    try:
        cleaned = out.strip().strip("`").removeprefix("json").strip()
        return json.loads(cleaned)
    except Exception:
        start, end = out.find("{"), out.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(out[start : end + 1])
            except Exception:
                return None
    return None


def review_verification(verify_type: str, file_path: str) -> dict | None:
    """验资材料 AI 初审:识别金额/日期/户名,输出报告"""
    p = Path(file_path)
    if not p.exists():
        return None
    parts: list[dict] = []
    ext = p.suffix.lower()
    if ext in (".mp4", ".mov"):
        frames = _extract_frames(p)
        if not frames:
            return {"report": "视频抽帧失败(请检查文件)", "flagged": True}
        for f in frames:
            parts.append(_image_part(f))
    elif ext == ".pdf":
        parts.append(_inline_part(p, "application/pdf"))
    elif ext in (".jpg", ".jpeg", ".png", ".webp"):
        parts.append(_image_part(p))
    else:
        return None

    type_hint = {
        "video": "视频验资(3日内录制,画面需展示账户余额与当前日期)",
        "balance_photo": "账户余额照片(需体现日期)",
        "bank_certificate": "银行资信证明(1个月内开具)",
        "guarantee_letter": "上级控股方担保证明",
    }.get(verify_type, "验资材料")

    prompt = (
        f"你是验资材料审核助手。这是{type_hint}。请识别并只输出 JSON:"
        '{"amount":识别到的金额(字符串,无则""),"date_text":识别到的日期(字符串,无则""),'
        '"account_name":识别到的户名/主体名称(字符串,无则""),"issues":存疑点数组(如日期缺失、金额不清晰、'
        '户名不一致等,无问题则[]),"summary":一句话概括识别结果}'
    )
    parts.append({"text": prompt})
    out = _call(parts)
    if not out:
        return None
    try:
        cleaned = out.strip().strip("`").removeprefix("json").strip()
        return json.loads(cleaned)
    except Exception:
        start, end = out.find("{"), out.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(out[start : end + 1])
            except Exception:
                return {"report": out, "flagged": False}
    return None


def _image_part(p: Path) -> dict:
    b64 = base64.b64encode(p.read_bytes()).decode("utf-8")
    mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}.get(
        p.suffix.lower().lstrip("."), "image/jpeg"
    )
    return {"inline_data": {"mime_type": mime, "data": b64}}


def _inline_part(p: Path, mime: str) -> dict:
    b64 = base64.b64encode(p.read_bytes()).decode("utf-8")
    return {"inline_data": {"mime_type": mime, "data": b64}}


def _video_duration(video: Path) -> float:
    """用 ffmpeg -i 探测时长(解析 stderr 的 Duration 字段,免去 ffprobe 依赖)"""
    import re

    try:
        probe = subprocess.run(
            [settings.ffmpeg_path, "-i", str(video)],
            capture_output=True, text=True, timeout=30,
        )
        m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", probe.stderr or "")
        if m:
            h, mm, s = m.groups()
            return int(h) * 3600 + int(mm) * 60 + float(s)
    except Exception:
        pass
    return 0.0


def _extract_frames(video: Path, count: int = 3) -> list[Path]:
    frames: list[Path] = []
    tmp = tempfile.mkdtemp(prefix="sclink_frames_")
    try:
        duration = _video_duration(video)
        if duration <= 0:
            points = [0.0]
        else:
            points = sorted({min(duration * f, max(duration - 0.5, 0.0)) for f in (0.05, 0.5, 0.9)})
        points = [max(0.0, x) for x in points if x >= 0]
        for i, ts in enumerate(points):
            out = Path(tmp) / f"frame_{i}.jpg"
            subprocess.run(
                [settings.ffmpeg_path, "-v", "error", "-ss", str(ts), "-i", str(video), "-frames:v", "1", "-q:v", "3", str(out)],
                capture_output=True, timeout=60,
            )
            if out.exists():
                frames.append(out)
        return frames
    except Exception:
        return frames


def order_summary(order_info: dict, tracks: list[dict]) -> str | None:
    """跟单 AI:订单智能摘要"""
    prompt = (
        "你是供应链订单跟进助手。根据订单信息和跟踪事件时间线,用一段话概括订单当前状态"
        "(进度、资金、风险、下一步建议),150 字以内,中文,直接输出正文不要标题。\n\n"
        f"订单信息:{json.dumps(order_info, ensure_ascii=False, default=str)}\n"
        f"跟踪事件:{json.dumps(tracks, ensure_ascii=False, default=str)}"
    )
    return _call([{"text": prompt}])


def extract_track_events(text: str) -> list[dict] | None:
    """跟单 AI:沟通内容 → 跟踪事件草稿"""
    prompt = (
        "你是供应链订单跟进助手。从下面的沟通记录中提取关键跟踪事件。只输出 JSON 数组,不要其他文字。"
        '每个事件字段:category(分类:货源/资金/到货/交付/违约/其他)、title(简短标题)、'
        'content(事件内容)、next_action(建议的下一步,无则空串)。最多 5 条,按时间顺序。\n\n沟通记录:\n' + text
    )
    out = _call([{"text": prompt}])
    if not out:
        return None
    try:
        cleaned = out.strip().strip("`").removeprefix("json").strip()
        data = json.loads(cleaned)
        return data if isinstance(data, list) else None
    except Exception:
        start, end = out.find("["), out.rfind("]")
        if start >= 0 and end > start:
            try:
                data = json.loads(out[start : end + 1])
                return data if isinstance(data, list) else None
            except Exception:
                return None
    return None
