"""Thin client for the public Bilibili web APIs used by this project.

Only endpoints that work without login are used:
- ``/x/web-interface/view``          video metadata (aid / cid / title / duration / pages)
- ``/x/player/playurl``              DASH stream URLs (we only need the audio track)
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field

import requests

API_VIEW = "https://api.bilibili.com/x/web-interface/view"
API_PLAYURL = "https://api.bilibili.com/x/player/playurl"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

_BVID_RE = re.compile(r"(BV[a-zA-Z0-9]{10})")


class BilibiliError(RuntimeError):
    """Raised when a Bilibili API call fails."""


@dataclass
class VideoPage:
    """One part (分P) of a video."""

    page: int
    cid: int
    title: str
    duration: int


@dataclass
class VideoInfo:
    bvid: str
    aid: int
    title: str
    desc: str
    duration: int
    owner: str
    pubdate: int
    pages: list[VideoPage] = field(default_factory=list)


def parse_bvid(text: str) -> str:
    """Extract a BV id from a bare id or a full video URL."""
    m = _BVID_RE.search(text.strip())
    if not m:
        raise BilibiliError(f"无法识别 BV 号: {text!r}")
    return m.group(1)


def _session(referer: str) -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT, "Referer": referer})
    return s


def _get_json(session: requests.Session, url: str, params: dict, retries: int = 5) -> dict:
    """GET with backoff for rate limiting (code -799) and risk control (HTTP 412).

    Bilibili aggressively rate-limits anonymous API access. A 412 usually
    clears on its own after a short wait; we retry a few times before
    giving up with an actionable error message.
    """
    last: Exception | None = None
    for attempt in range(retries):
        try:
            r = session.get(url, params=params, timeout=30)
            if r.status_code == 412 and attempt < retries - 1:
                time.sleep(5 * (attempt + 1))
                continue
            r.raise_for_status()
            data = r.json()
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 412:
                last = BilibiliError(
                    "B 站风控拦截（HTTP 412）：当前网络请求过于频繁，"
                    "请等待几分钟后再试；也可以尝试更换网络环境。"
                )
                break
            last = e
        except Exception as e:  # network / JSON errors
            last = e
        else:
            if data.get("code") == 0:
                return data["data"]
            if data.get("code") == -799 and attempt < retries - 1:
                time.sleep(2 ** attempt * 2)
                continue
            raise BilibiliError(f"Bilibili API 错误 {data.get('code')}: {data.get('message')}")
        time.sleep(2 ** attempt)
    raise BilibiliError(f"请求失败: {last}")


def get_video_info(bvid: str) -> tuple[VideoInfo, requests.Session]:
    """Fetch metadata for a video. Returns (info, session to reuse)."""
    bvid = parse_bvid(bvid)
    session = _session(f"https://www.bilibili.com/video/{bvid}/")
    data = _get_json(session, API_VIEW, {"bvid": bvid})
    pages = [
        VideoPage(page=p["page"], cid=p["cid"], title=p.get("part") or data["title"],
                  duration=p["duration"])
        for p in data.get("pages", [])
    ]
    info = VideoInfo(
        bvid=data["bvid"],
        aid=data["aid"],
        title=data["title"],
        desc=data.get("desc", ""),
        duration=data["duration"],
        owner=data["owner"]["name"],
        pubdate=data["pubdate"],
        pages=pages,
    )
    return info, session


def get_audio_url(session: requests.Session, aid: int, cid: int) -> str:
    """Return the direct URL of the best available DASH audio stream."""
    data = _get_json(
        session, API_PLAYURL,
        {"avid": aid, "cid": cid, "qn": 80, "fnval": 16, "fourk": 1},
    )
    audios = (data.get("dash") or {}).get("audio") or []
    if not audios:
        raise BilibiliError("该视频没有可用的音频流（可能是付费/会员专享内容）")
    audios.sort(key=lambda a: a.get("bandwidth", 0), reverse=True)
    return audios[0]["base_url"]


def download(session: requests.Session, url: str, dest: str,
             referer: str, chunk: int = 1 << 20) -> str:
    """Download a URL to *dest* with a progress bar. Returns *dest*."""
    from tqdm import tqdm

    headers = {"User-Agent": USER_AGENT, "Referer": referer}
    with session.get(url, headers=headers, stream=True, timeout=60) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        with open(dest, "wb") as f, tqdm(
            total=total, unit="B", unit_scale=True, desc="下载音频"
        ) as bar:
            for data in r.iter_content(chunk):
                f.write(data)
                bar.update(len(data))
    return dest
