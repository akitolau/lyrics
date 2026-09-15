# 歌词 · 三张专辑

Akito Lau 的三张专辑歌词在线版。

**在线阅读：https://akitolau.github.io/lyrics/**

| 专辑 | 曲目 | 有词 |
|---|---|---|
| Seasons of Music | 15 | 12 |
| 都市失语纪 Lost in Metropolitan | 14 | 13 |
| 怪谈 | 11 | 10 |
| **合计** | **40** | **35** |

---

## 文件说明

| 文件 | 说明 |
|---|---|
| `index.html` | 网页（单文件、零依赖、可离线打开、支持手机） |
| `source/*.md` | 歌词源文件（这里改词） |
| `lyrics.json` | 由源文件解析出的结构化数据 |
| `build.py` | 构建脚本：读 `source/*.md` → 生成 `index.html` + `lyrics.json` |

## 更新歌词

1. 改 `source/` 下的 md（保持原格式：`# 专辑名` → `数字. 曲名` → 逐行歌词，空行分隔）
2. 构建：

```bash
python3 build.py
```

3. 提交推送：

```bash
git add -A && git commit -m "update: <说明>" && git push
```

推送到 `main` 后 GitHub Pages 约 1 分钟自动更新。

### 构建脚本的两个约定

- **双语对照**（英文原词 + 中文译词，成对排版）**只对 `build.py` 里 `PAIR` 名单内的曲目启用**。因为有些歌的中英行是「交错但语义错位」的（如《Wilderness》），逐句配对会配错。名单之外的候选会在构建时打印告警，确认后再决定是否加入。
- **器乐曲目**：标题后写「此首为器乐」即识别为器乐，不显示歌词。

---

© 2026 Akito Lau 版权所有 · ALL RIGHTS RESERVED · 未经许可，请勿转载
