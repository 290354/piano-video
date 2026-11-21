# Piano Video Pipeline

一条命令从零到成片：作曲 → 母带 → Canvas 逐帧 → H.264/AAC。

```bash
# 冒烟测试（约 30 秒）
python3 make.py --preview 4 --out /tmp/test.mp4

# 正式成片（1080p，约 5–6 分钟）
python3 make.py --out ../out/nocturne.mp4

# 换一首曲子：外部乐谱
python3 make.py --score scores/waltz.json --out ../out/waltz.mp4

# 更慢、更低的调，4K
python3 make.py --bpm 64 --transpose -2 --scale 2 --out ../out/nocturne_4k.mp4
```

## 文件

| 文件 | 作用 |
| --- | --- |
| `make.py` | 总入口：采样准备、作曲、母带、写配置、渲染、封面 |
| `compose.py` | 内置乐谱（21 小节 A 小调夜曲）+ 采样合成引擎 |
| `score_loader.py` | 外部 `score.json` → 音符事件；和弦按音程表解析，含和弦音吸附、十种织体、`bassLine`、旋律变化音 |
| `critic2.py` | 评审器 v2：动机变形、织体、低音、和声色彩、离调密度 |
| `scores/` | 乐谱格式说明与示例（`waltz.json`） |
| `scene.js` | 画面，`drawFrame(t)` 是时间的纯函数 |
| `render.py` | 无头 Chromium 逐帧截屏 → image2pipe → x264 |
| `index.html` | 挂载 canvas 与 config/notes/scene |
| `assets/samples/*.ogg` | Salamander Grand Piano 采样（CC-BY 3.0） |

## 换一首曲子

不改 Python，只写 JSON。格式见 [`scores/README.md`](scores/README.md)：

```json
{
  "key": "D", "mode": "minor", "meter": [3, 4], "bpm": 96,
  "pattern": "waltz",
  "chords": ["Dm", "Gm", "A", "Dm"],
  "melody": [[0, 0, 1.5, 4, 0, 0.78], [0, 1.5, 1, 2, 1, 0.72]]
}
```

旋律六元组是 `[小节, 拍, 时值, 音级, 八度, 力度]`，可选第 7 位是半音偏移；音级指音阶级数而非半音。整数拍上不协和的音会自动吸附到当前小节的和弦音。左手由 `pattern` 生成：`nocturne` / `waltz` / `block` / `arpeggio`，以及后加的 `pulse` / `ostinato` / `counter` / `drone` / `broken` / `waltz2`——后六种的低音不在第 1 拍，是打破「每首听起来都一样」的关键。和弦支持七/九/挂留/变化音与转位。曲名、调性、BPM、键盘音域都会跟随 score。


## 流程细节

**音频**
- 每个音符就近取采样，`resample_poly` 按音高比重采样；采样 44.1 kHz，混音 48 kHz，读入时先统一采样率（否则整体低约 1.5 个半音，已修）
- 力度控制音量 `0.16 + 0.84·v^1.7` 与低通截止 `2200 + 13500·v^1.15`
- 离键后按 `exp(-t/0.85)` 衰减（模拟踏板），4 ms 淡入防爆音
- 声像：旋律 +0.10、伴奏 −0.08、高音装饰 +0.26
- 卷积混响：3 s 指数衰减 IR + 4 个早反射，干湿 0.92 / 0.30

**母带**
- `highpass 32 Hz`、`260 Hz −1.6 dB`、`3.2 kHz +2.2 dB`
- 结尾 3.6 s 淡出
- 两遍 loudnorm 到 −14 LUFS / TP −1.5，第二遍用 linear 模式

**画面**
- 逻辑坐标 1920×1080，`pixelRatio` 控制实际像素（2 = 4K 矢量重绘）
- 键盘 40–84（E2–C6，随移调平移），白键渐变 + 每键微色差 + 黑键投影 + 前档条
- 音符条：渐变、顶部拖尾、落点亮边，打击时键位光晕
- 键盘下方镜像倒影（blur 7px，透明度 0.38，纵向压扁 0.62）
- 暗角只压到琴键上方，避免把键盘压灰

## 依赖

```bash
pip3 install scipy numpy playwright imageio-ffmpeg
python3 -m playwright install chromium
```

系统 ffmpeg 可能没编 libx264，`render.py` 用 `imageio-ffmpeg` 自带的二进制。

## 采样授权

Salamander Grand Piano by Alexander Holm，CC-BY 3.0。
对外发布请保留片尾 `钢琴采样 · Salamander Grand Piano` 署名（`--credit2` 可改文案，不建议删）。
