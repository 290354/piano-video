# 乐谱 · Sheet Music

每日钢琴曲的双谱表完整乐谱。音符不是重新编配的：和视频音轨用的是同一份
`score.json`，经 `pipeline/score_loader.py` 展开成音符事件后再排版，所以每个音、
每处力度与速度变化都和成片对得上。

| 日期 | 曲名 | 调性 · 速度 · 小节 | 时长 | 下载 |
| --- | --- | --- | --- | --- |
| 2026-11-14 | 晨雾 | E 小调 · 66 BPM · 16 小节 | 64.2 s | [PDF](daily_20261114.pdf) · [MSCZ](daily_20261114.mscz) · [XML](daily_20261114.musicxml) |
| 2026-11-15 | 露水 | G 小调 · 64 BPM · 22 小节 | 93.8 s | [PDF](daily_20261115.pdf) · [MSCZ](daily_20261115.mscz) · [XML](daily_20261115.musicxml) |
| 2026-11-16 | 旧信 | A 小调 · 60 BPM · 23 小节 | 104.3 s | [PDF](daily_20261116.pdf) · [MSCZ](daily_20261116.mscz) · [XML](daily_20261116.musicxml) |
| 2026-11-17 | 窄巷 | C 小调 · 108 BPM · 23 小节 | 45.2 s | [PDF](daily_20261117.pdf) · [MSCZ](daily_20261117.mscz) · [XML](daily_20261117.musicxml) |
| 2026-11-18 | 海雾 | 升F 小调 · 72 BPM · 24 小节 | 69.1 s | [PDF](daily_20261118.pdf) · [MSCZ](daily_20261118.mscz) · [XML](daily_20261118.musicxml) |
| 2026-11-19 | 灯塔 | 降B 小调 · 58 BPM · 22 小节 | 103.6 s | [PDF](daily_20261119.pdf) · [MSCZ](daily_20261119.mscz) · [XML](daily_20261119.musicxml) |
| 2026-11-20 | 归鸟 | D 小调 · 68 BPM · 24 小节 | 95.7 s | [PDF](daily_20261120.pdf) · [MSCZ](daily_20261120.mscz) · [XML](daily_20261120.musicxml) |
| 2026-11-21 | 灯河 | B 小调 · 68 BPM · 24 小节 | 97.5 s | [PDF](daily_20261121.pdf) · [MSCZ](daily_20261121.mscz) · [XML](daily_20261121.musicxml) |

## 三种格式怎么选

| 格式 | 用途 |
| --- | --- |
| `.mscz` | **MuseScore Studio 工程文件**，双击即开。可播放、改音符、转调、拆声部、导出分谱或 MP3。 |
| `.musicxml` | 通用交换格式，Sibelius / Finale / Dorico / Logic / GarageBand 都能导入。 |
| `.pdf` | A4 单页，直接看或打印，无需装软件。 |

## 记谱说明

- **右手**是旋律声部；**左手**分两个声部：低音（每小节根音）与琶音/和弦织体。
- 原引擎里 `nocturne` 织体每小节六等分，谱面按**三连音**记谱（每拍两个三连音八分），时值与音频一致。
- `arpeggio` 织体按十六分音符记谱；`block` 为持续和弦；`waltz` 为低音+两拍和弦。
- 段落标记（A / B / A′ / Coda）、力度（p / mp / mf）、速度变化与 `rit.` 均按 `score.json` 标注。
- 引擎的 `sparkle` 八度加倍属于混音效果（音量仅 22%），不写进谱面，否则会出现一条多余的八度旋律。
- 曲末长音若超出最后一小节，谱面按实际可容纳时值收尾，不产生悬空延音线。

## 重新生成

```bash
python3 pipeline/critic.py --history scores scores/daily_20261121.json   # 复核分数
# 谱面生成脚本随仓库提供：tools/make_sheet.py
python3 tools/make_sheet.py scores/daily_20261121.json out/sheet/daily_20261121.musicxml
mscore3 -o out/sheet/daily_20261121.pdf out/sheet/daily_20261121.musicxml
```
