# 夜曲 · Nocturne in A minor

一段 74 秒的钢琴曲视频：曲子由代码写成，画面由代码逐帧绘制，没有用 AI 视频模型，也没有现成画面素材。

## 成片

- `nocturne_in_a_minor.mp4` — 1920×1080 / 30 fps / H.264 High + AAC 192k，74.3 s，22 MB
- `cover.jpg` — 片头画面，可直接当封面

## 曲子

| 项目 | 值 |
| --- | --- |
| 调性 | A 小调 |
| 速度 | 72 BPM，四四拍 |
| 结构 | 引子 2 小节 → A 段 8 小节 → B 段 4 小节 → A' 4 小节 → 尾声 3 小节 |
| 音符 | 239 个事件（旋律 66 / 琶音 148 / 低音 18 / 高八度 7） |
| 和声 | Am–F–C–G｜Am–F–Dm–E｜F–C–G–Am｜Am–F–C–G｜F–E–Am |
| 母带 | −14.0 LUFS，真峰值 −3.4 dBFS |

> **v2 修正**：初版音频把 44.1 kHz 采样当成 48 kHz 使用，整体低了约 1.5 个半音（标称 A 小调，实际接近 G# 小调）。现已修正，A1 实测 54.93 Hz（理论 55.00），画面未变。

## 引擎 v2：候选 + 评审

v1 的每天一曲是「写一版就渲染」，语法不变、只换参数，听感上像同一首曲子的第 N 个实例。v2 改了三件事：

| 改动 | 具体做法 |
| --- | --- |
| 乐谱能写出段落 | `sections` 给每段独立的织体与力度（`nocturne` / `arpeggio` / `waltz` / `block`），A–B–A′–Coda 不再是一个密度 |
| 速度可以变 | `tempo.map` 按小节插值，`tempo.rit` 收尾渐慢；`compose.py` 把拍位置积分成秒 |
| 左手有声部进行 | `voicing: "lead"` 取离上一小节最近的转位；低音固定落在 E2–E3，键盘不会铺成五个八度 |
| 有选择压力 | 每天写 6 个候选，`critic.py` 按 8 项指标打分排序，只渲染赢家 |

`critic.py` 的 8 项指标：级进率、音域、音高多样性、力度层次、段落密度对比、动机重复、对旧作的新颖度、终止式。它衡量的是结构是否立得住，不是好不好听——但同一时段写出的几个候选之间，排序是可靠的。

实测（2026-11-14）：旧引擎的《晨雾》51.1 分、《小圆舞》71.9 分；v2 的两个候选 97.5 / 90.7，赢了才拿去渲染。

## 工作流

`pipeline/` 是一条可以重复跑的流水线，一条命令从零到成片。

```bash
# 冒烟测试：4 秒，约 30 秒出结果
python3 pipeline/make.py --preview 4 --out /tmp/probe.mp4

# 现状成片（1080p，约 5–6 分钟）
python3 pipeline/make.py --out out/nocturne.mp4

# 换一首曲子：写 score.json，其余不用动
python3 pipeline/make.py --score pipeline/scores/waltz.json --out out/waltz.mp4

# 4K、更慢、降两个半音
python3 pipeline/make.py --bpm 64 --transpose -2 --scale 2 --out out/nocturne_4k.mp4
```

| 阶段 | 文件 | 做什么 |
| --- | --- | --- |
| 采样 | `assets/samples/*.ogg` | Salamander 30 个采样，首次运行自动解码为 wav |
| 作曲 | `compose.py` | 内置夜曲乐谱，或 `--score` 读外部 JSON |
| 合成 | `compose.py` | 按音高重采样、力度控音量与亮度、踏板包络、卷积混响 |
| 母带 | `make.py` | EQ + 淡出 + 两遍 loudnorm 到 −14 LUFS |
| 画面 | `scene.js` | `drawFrame(t)` 是时间的纯函数：夜空、浮尘、下落音符、琴键、打击光晕、倒影、暗角、颗粒、标题 |
| 编码 | `render.py` | 无头 Chromium 逐帧截图 → image2pipe → x264/aac |
| 封面 | `make.py` | 抽 3.0 秒帧 |

### 让模型现写一首

不必改 Python。读 `pipeline/scores/README.md`，写一份 JSON 即可：

```json
{
  "key": "D", "mode": "minor", "meter": [3, 4], "bpm": 96,
  "pattern": "waltz",
  "chords": ["Dm", "Gm", "A", "Dm"],
  "melody": [[0, 0, 1.5, 4, 0, 0.78], [0, 1.5, 1, 2, 1, 0.72]]
}
```

`melody` 的六元组是 `[小节, 拍, 时值, 音级, 八度, 力度]`。音级是**音阶级数**（0 = 主音），不是半音；整数拍上不协和的音会自动吸附到当前小节的和弦音，所以粗写也不会刺耳。左手由 `pattern` 生成（`nocturne` / `waltz` / `block` / `arpeggio`）。曲名、调性、BPM、键盘音域都会跟着 score 走。

示例：`pipeline/scores/waltz.json`（D 小调圆舞曲，16 小节）。

## 目录

```
nocturne_in_a_minor.mp4
cover.jpg
README.md
pipeline/
  make.py           总入口
  compose.py        乐谱（内置）+ 合成引擎
  score_loader.py   外部 score.json → 音符事件
  scene.js          画面
  render.py         截帧编码
  index.html
  scores/           乐谱格式说明 + 示例
  assets/samples/   Salamander 采样（6.7 MB ogg）
  README.md         流水线细节
out/                新产出放这里
sheet/              每日乐谱（PDF / MSCZ / MusicXML）
tools/              make_sheet.py，score.json → 五线谱
```

## 素材与授权

- 钢琴音源：**Salamander Grand Piano V3**，Alexander Holm 录制，CC-BY 3.0，经 Tone.js CDN 取样（30 个音，A0–C8，就近音重采样）。对外发布请保留片尾署名。
- 字体：Noto Serif Display / Noto Serif CJK SC（SIL OFL）。
- 乐谱、画面、混音均为本项目生成，可自由使用。

## 原始方法来源

按两个 GitHub 技能的做法实现：

1. [illodev/drawn-by-code](https://github.com/illodev/drawn-by-code) 的 `sound` —— 先定速度与拍点，画面跟着音乐走；音乐自己合成以规避版权；不看波形不下结论；母带压到 −14 LUFS。
2. [changroro/code-video](https://github.com/changroro/code-video) 的 `code-video` —— 每一帧是时间的纯函数 `drawFrame(t)`；Canvas 画帧、无头 Chrome 截帧、ffmpeg 编码；先审静帧再渲全片。

GitHub 拉整仓很慢，实际是读了两个仓库的 `SKILL.md`，按其方法自建管线，没有套用它们的模板代码。

## 每日产出

仓库里每天多一首，视频走 Release，乐谱与封面进 git。

| 日期 | 曲名 | 调性 | 时长 | Release |
| --- | --- | --- | --- | --- |
| 2026-11-14 | 晨雾 | E 小调 · 66 BPM · 16 小节 | 64.2 s | [daily-20261114](https://github.com/290354/piano-video/releases/tag/daily-20261114) |
| 2026-11-15 | 露水 | G 小调 · 64 BPM · 22 小节 | 93.8 s | [daily-20261115](https://github.com/290354/piano-video/releases/tag/daily-20261115) |
| 2026-11-16 | 旧信 | A 小调 · 60 BPM · 23 小节 | 104.3 s | [daily-20261116](https://github.com/290354/piano-video/releases/tag/daily-20261116) |
| 2026-11-17 | 窄巷 | C 小调 · 108 BPM · 23 小节 | 45.2 s | [daily-20261117](https://github.com/290354/piano-video/releases/tag/daily-20261117) |
| 2026-11-18 | 海雾 | 升F 小调 · 72 BPM · 24 小节 | 69.1 s | [daily-20261118](https://github.com/290354/piano-video/releases/tag/daily-20261118) |
| 2026-11-19 | 灯塔 | 降B 小调 · 58 BPM · 22 小节 | 103.6 s | [daily-20261119](https://github.com/290354/piano-video/releases/tag/daily-20261119) |
| 2026-11-20 | 归鸟 | D 小调 · 68 BPM · 24 小节 | 95.7 s | [daily-20261120](https://github.com/290354/piano-video/releases/tag/daily-20261120) |
| 2026-11-21 | 灯河 | B 小调 · 68 BPM · 24 小节 | 97.5 s | [daily-20261121](https://github.com/290354/piano-video/releases/tag/daily-20261121) |
| 2026-11-22 | 雪信 | 升C 小调 · 82 BPM · 32 小节 | 87.6 s | [daily-20261122](https://github.com/290354/piano-video/releases/tag/daily-20261122) |
| 2026-11-21 | 铁轨 ↻ | D 多利亚 · 112 BPM · 24 小节 | 57.1 s | [rework-tracks](https://github.com/290354/piano-video/releases/tag/rework-tracks) |
| 2026-11-21 | 三月的信 ↻ | F 小调 · 76 BPM · 26 小节 | 66.3 s | [rework-letter](https://github.com/290354/piano-video/releases/tag/rework-letter) |
| 2026-11-21 | 铜与霜 ↻ | C 小调 · 63 BPM · 28 小节 | 113.7 s | [rework-brass](https://github.com/290354/piano-video/releases/tag/rework-brass) |

每首曲子的**双谱表乐谱**见 [`sheet/`](sheet/)：`.pdf` 直接看或打印，`.mscz` 用 MuseScore Studio 打开可编辑，`.musicxml` 可导入 Sibelius / Dorico / Logic。记谱与音轨同源，每个音都来自同一份 `score.json`。

### 2026-11-21 重写的三首（↻）

上面八首被指出织体单一、动机平淡、和声保守。量化之后三条都成立，而且比描述更彻底：
178 个和弦里七和弦 0 个，每一首的每一个低音都落在小节第 1 拍，动机只出现过原形。

根因不在乐谱而在管线：

- `score_loader.py` 的 `parse_chord` 只认三和弦与属七，`maj7 / 9 / sus4 / dim7 / b9` 全被静默降级；
  低音是硬编码的「每小节第 1 拍、整小节时值」。
- `critic.py` 的和声、织体、低音、节奏四项权重为 0，却把「级进率」设成 0.20 —— 它会给同质化的曲子打 82–100 分。
- `scores/README.md` 的作曲约定第 2 条写「以级进为主，三四度跳进每两小节最多一次」，第 12 条写「动机移高一级」。

三处都已改。三首新作各针对一条：

| 曲 | 针对 | 做法 |
| --- | --- | --- |
| 铁轨 | 织体 | 4 种 pattern 轮换 5 段；低音走 D–C–B–A–G–A 级进线条，不在第 1 拍 |
| 三月的信 | 动机 | 一个 4 音动机用原形/倒影/逆行/逆行倒影 4 种形态，出现 7 次 |
| 铜与霜 | 和声 | 降 II、导减七、副属 V/iv、maj7#11；力度曲线 0.62→1.00→0.44 |

`critic2` 得分 98.9 / 98.9 / 97.0；同一标准下旧八首是 34.8–50.7。
新代码在提交 `cf8b17fe`，谱面在 `f866def4`。旧八首的音频与谱面没有改动，事件哈希逐位校验过。
