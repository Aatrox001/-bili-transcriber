"""Command line interface: BV 号/链接 -> 逐字稿文件。"""

from __future__ import annotations

import argparse
import os
import sys
import tempfile

from . import bilibili
from .audio import load_wav_mono_16k, to_wav_16k
from .transcribe import EXPORTERS, transcribe


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="bili-transcribe",
        description="下载 B 站视频音频并转写为逐字稿（txt / srt / json）",
    )
    p.add_argument("video", help="BV 号或视频链接，例如 BV1YRHz6sEXL")
    p.add_argument("-o", "--output", default=None, help="输出文件路径（默认按视频标题命名）")
    p.add_argument("-f", "--format", choices=sorted(EXPORTERS), default="txt",
                   help="输出格式（默认 txt）")
    p.add_argument("-p", "--part", type=int, default=1,
                   help="分P 视频的第几P（默认 1）")
    p.add_argument("--model", default="small",
                   help="faster-whisper 模型: tiny/base/small/medium/large-v3（默认 small）")
    p.add_argument("--model-path", default=None,
                   help="本地模型目录（覆盖 --model，用于离线/手动下载模型的场景）")
    p.add_argument("--language", default="zh", help="转写语言（默认 zh）")
    p.add_argument("--keep-audio", action="store_true", help="保留下载的音频文件")
    p.add_argument("--device", default="cpu", help="cpu 或 cuda（默认 cpu）")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    print("获取视频信息…")
    info, session = bilibili.get_video_info(args.video)
    pages = info.pages
    if args.part < 1 or args.part > len(pages):
        print(f"错误: 该视频共 {len(pages)} P，没有第 {args.part} P", file=sys.stderr)
        return 1
    page = pages[args.part - 1]
    print(f"标题: {info.title}（UP主: {info.owner}）")
    if len(pages) > 1:
        print(f"分P: {page.page}/{len(pages)} - {page.title}")

    print("获取音频流地址…")
    audio_url = bilibili.get_audio_url(session, info.aid, page.cid)

    workdir = tempfile.mkdtemp(prefix="bili_transcribe_")
    raw = os.path.join(workdir, "audio.m4s")
    wav = os.path.join(workdir, "audio.wav")
    try:
        bilibili.download(
            session, audio_url, raw,
            referer=f"https://www.bilibili.com/video/{info.bvid}/",
        )
        print("转换音频格式…")
        to_wav_16k(raw, wav)
        samples = load_wav_mono_16k(wav)
        print(f"音频时长: {len(samples) / 16000:.1f} 秒，开始转写…")
        segments = transcribe(
            samples, model=args.model, model_path=args.model_path,
            language=args.language, device=args.device,
        )
    finally:
        if not args.keep_audio:
            for f in (raw, wav):
                if os.path.exists(f):
                    os.remove(f)

    out_path = args.output or f"{info.bvid}.{args.format}"
    meta = {"bvid": info.bvid, "title": info.title, "owner": info.owner,
            "duration": info.duration}
    if args.format == "json":
        content = EXPORTERS["json"](segments, meta)
    else:
        content = EXPORTERS[args.format](segments)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"已保存: {out_path}（共 {len(segments)} 段）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
