# bili-transcriber

把任意 B 站公开视频一键转成逐字稿。不需要登录 B 站账号。

原理很简单：调用 B 站公开接口拿到视频的音频流 → 下载 → 用 [faster-whisper](https://github.com/SYSTRAN/faster-whisper) 本地语音转文字。输出带时间戳的 `txt` / `srt` / `json`。

> English: download the audio track of any public Bilibili video and transcribe
> it locally with faster-whisper. No Bilibili login required. See
> [Quickstart](#quickstart) below.

## 效果示例

```text
[0.0-1.6] Hello 大家好
[1.6-4.0] 我一直有个习惯就是每天写日记
[4.0-6.8] 然后我这两天因为正好是十一
...
```

## Quickstart

```bash
# 1. 需要 ffmpeg（macOS: brew install ffmpeg；Ubuntu: apt install ffmpeg）
# 2. 安装依赖
pip install -r requirements.txt

# 3. 转写（BV 号或完整链接都可以）
python -m bili_transcriber BV1YRHz6sEXL
# 输出: BV1YRHz6sEXL.txt

# 输出 srt 字幕文件
python -m bili_transcriber BV1YRHz6sEXL -f srt -o output.srt

# 换更大的模型（更准、更慢），或指定语言
python -m bili_transcriber BV1YRHz6sEXL --model medium --language zh

# 分P 视频取第 2 P
python -m bili_transcriber BV1xxxx -p 2
```

第一次运行时 faster-whisper 会自动从 HuggingFace 下载模型（`small` 约 460MB）。如果下载有困难，可以手动下载模型文件后用 `--model-path` 指定本地目录：

```bash
python -m bili_transcriber BV1YRHz6sEXL --model-path /path/to/faster-whisper-small
```

## 完整参数

```
usage: bili-transcribe [-h] [-o OUTPUT] [-f {json,srt,txt}] [-p PART]
                       [--model MODEL] [--model-path MODEL_PATH]
                       [--language LANGUAGE] [--keep-audio] [--device DEVICE]
                       video

positional arguments:
  video                 BV 号或视频链接，例如 BV1YRHz6sEXL

options:
  -o, --output OUTPUT   输出文件路径（默认按视频标题命名）
  -f, --format          输出格式: txt / srt / json（默认 txt）
  -p, --part PART        分P 视频的第几P（默认 1）
  --model MODEL         faster-whisper 模型: tiny/base/small/medium/large-v3（默认 small）
  --model-path          本地模型目录（覆盖 --model）
  --language LANGUAGE   转写语言（默认 zh）
  --keep-audio          保留下载的音频文件
  --device DEVICE       cpu 或 cuda（默认 cpu）
```

## 工作原理

```
视频链接/BV号
    │  /x/web-interface/view（公开接口，无需登录）
    ▼
aid / cid / 标题 / 时长 / 分P 信息
    │  /x/player/playurl（公开接口）
    ▼
DASH 音频流地址 ──下载──▶ m4s ──ffmpeg──▶ 16kHz 单声道 wav
    │  faster-whisper（本地转写，无需联网）
    ▼
带时间戳的逐字稿（txt / srt / json）
```

## 局限

- 仅支持**公开**视频：付费 / 会员专享 / 已下架的视频拿不到音频流。
- B 站接口有频率限制，遇到 `请求过于频繁` 等一会儿再试（程序会自动重试几次）。
- 转写准确率取决于模型：`small` 对中文口语效果不错，人名、专有名词、中英混说偶尔会错；要更高精度可以用 `medium` / `large-v3`（更慢）。
- 长视频在 CPU 上转写较慢（约 3~5 倍音频时长），有 GPU 时加 `--device cuda`。
- 只转写**声音**内容，不含弹幕和评论区。

## 免责

本项目仅用于学习与个人使用。请遵守 B 站用户协议与相关法律法规，不要将转写内容用于侵犯他人版权的用途。

## License

MIT
