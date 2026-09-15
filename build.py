#!/usr/bin/env python3
"""
精选专辑歌词页构建
  输入：source/*.md（用户提供的最新曲目与歌词）
  输出：lyrics.json（结构化数据）+ index.html（展现页面）
用法：  python3 build.py
"""
import html, json, os, re, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "source")

# 源文件 → 专辑元信息。顺序即页面里的切换顺序。
ALBUMS = [
    {
        "key": "seasons",
        "file": "Seasons of Music.md",
        "en": "Seasons of Music",
        "cn": "",
        "accent": "#2A4A6A",          # 藍
        "accent_soft": "rgba(42,74,106,.30)",
    },
    {
        "key": "metro",
        "file": "都市失语纪 Lost in Metropolitan.md",
        "en": "Lost in Metropolitan",
        "cn": "都市失语纪",
        "accent": "#E87A90",          # 桜
        "accent_soft": "rgba(232,122,144,.34)",
    },
    {
        "key": "guaitan",
        "file": "怪谈.md",
        "en": "怪谈",
        "cn": "",
        "accent": "#5A4A6E",          # 墨紫
        "accent_soft": "rgba(90,74,110,.34)",
    },
]

# 双语对照（英文原词 + 中文译词）只对名单内曲目启用——
# 因为有些歌的中英行是「交错但语义错位」的，逐句配对会配错（如怪谈 #2 Wilderness）。
# 名单外的双语候选会在构建时告警，由人确认后再决定加不加。
PAIR = {"seasons": [2, 5, 7, 8, 11], "guaitan": [1, 8]}

CN_NUM = {1: "一", 2: "两", 3: "三", 4: "四", 5: "五"}

MODS = []          # 记录所有对原文的机械修正，交付时如实汇报
WARN = []          # 需要人确认的判断项

CJK = re.compile(r"[\u4e00-\u9fff]")
KANA = re.compile(r"[\u3040-\u30ff]")
LAT = re.compile(r"[A-Za-z]")


def clean(s):
    """修掉 markdown 导出转义与明显的排版手误。只做机械修正，不改词句。"""
    o = s
    s = re.sub(r"\\([\\`*_{}\[\]()#+\-.!~<>])", r"\1", s)   # \- \. 等转义 → 原字符
    s = re.sub(r"([\u2018\u2019])[ \u3000]+(?=[A-Za-z])", r"\1", s)  # We’ re → We’re
    s = re.sub(r"\bI(don't|don\u2019t)\b", lambda m: "I " + m.group(1), s)  # Idon't → I don't
    s = s.rstrip()
    if s != o:
        MODS.append((o, s))
    return s


def kind(line):
    has_cjk = bool(CJK.search(line))
    has_lat = bool(LAT.search(line))
    has_kana = bool(KANA.search(line))
    if (has_lat or has_kana) and not has_cjk:
        return "en"                     # 纯拉丁 / 纯假名 → 视为「原词行」
    if has_cjk and not has_lat and not has_kana:
        return "cn"
    return "mix" if (has_lat or has_kana) else "cn"


def parse(path, meta):
    lines = open(path, encoding="utf-8").read().split("\n")
    album_note, songs, cur = "", [], None

    for raw in lines:
        t = raw.strip()
        if not t:
            continue
        if t.startswith("# "):                                  # 专辑大标题
            continue
        if t.startswith("*") and t.endswith("*") and not cur:   # 专辑说明
            album_note = clean(t.strip("*")).strip("（）")
            continue
        m = re.match(r"^(\d+)\.\s*(.+?)\s*$", t)
        if m:                                                    # 曲目开始
            title = clean(m.group(2))
            en = cn = ""
            mm = re.search(r"([A-Za-z].*?)(?=[\u4e00-\u9fff])", title)
            if mm and CJK.search(title):
                en, cn = mm.group(1).strip(), title[mm.end():].strip()
            elif LAT.search(title) and not CJK.search(title):
                en = title
            else:
                cn = title
            cur = {"no": int(m.group(1)), "title": title, "en": en, "cn": cn,
                   "note": "", "lines": []}
            songs.append(cur)
            continue
        if cur is None:
            continue
        line = clean(t)
        if not cur["lines"] and not cur["note"] and re.match(r"^（.*）$", line):
            cur["note"] = line.strip("（）")                     # 曲目附注（如「采样：…」）
            continue
        if re.search(r"器乐", line) and not cur["lines"]:
            cur["note"] = line.strip("（）")                     # 「此首为器乐」→ 器乐曲目
            cur["force_instr"] = True
            continue
        cur["lines"].append(line)

    # —— 双语配对：仅对 PAIR 名单内的曲目启用（避免语义错位的歌被误配）——
    allow = PAIR.get(meta["key"], [])
    for s in songs:
        ks = [kind(l) for l in s["lines"]]
        i, cand, paired = 0, [], 0
        while i < len(s["lines"]):
            if ks[i] == "en" and i + 1 < len(ks) and ks[i + 1] == "cn":
                cand.append({"t": "pair", "en": s["lines"][i], "cn": s["lines"][i + 1]})
                paired += 2
                i += 2
            else:
                cand.append({"t": "line", "k": ks[i], "x": s["lines"][i]})
                i += 1
        candidate = (paired >= 0.8 * len(ks)) and paired >= 6
        enabled = s["no"] in allow
        if candidate and not enabled:
            WARN.append(f'{meta["key"]} #{s["no"]} {s["title"]}：检测到 {paired} 行中英交替，'
                        f'但不在配对名单 → 按源文交错顺序原样呈现')
        if enabled and not candidate:
            WARN.append(f'{meta["key"]} #{s["no"]} {s["title"]}：在配对名单中，'
                        f'但未检测到稳定的中英交替 → 未配对，请复核')
        s["bilingual"] = bool(enabled and candidate)
        s["blocks"] = cand if s["bilingual"] else [
            {"t": "line", "k": ks[j], "x": s["lines"][j]} for j in range(len(ks))]
        s["nlines"] = len(s["lines"])
        s["instrumental"] = (len(s["lines"]) == 0) or bool(s.get("force_instr"))

    return {"key": meta["key"], "en": meta["en"], "cn": meta["cn"],
            "accent": meta["accent"], "accent_soft": meta["accent_soft"],
            "note": album_note, "songs": songs}


def esc(s):
    return html.escape(s, quote=False)


# ────────────────────────────── CSS ──────────────────────────────
CSS = """
:root{
  --paper:#F5F0E0; --ink:#2E2C27; --ink-soft:#494640;
  --muted:#8E887B; --muted-2:#A9A395;
  --line:rgba(46,44,39,.13); --line-soft:rgba(46,44,39,.07);
  --sakura:#E87A90; --ai:#2A4A6A;
  --serif:"Songti SC","STSong","Source Han Serif SC","Noto Serif SC",serif;
  --kai:"LXGW WenKai","霞鹜文楷","Kaiti SC","楷体-简","STKaiti",serif;
  --sans:-apple-system,BlinkMacSystemFont,"PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif;
  --acc:var(--ai); --acc-soft:rgba(42,74,106,.30);
  --lyr:24em;
}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%;scroll-behavior:smooth}
body{margin:0;background:var(--paper);color:var(--ink);
  font-family:var(--kai);font-size:17px;line-height:2.0;-webkit-font-smoothing:antialiased;
  background-image:
    repeating-linear-gradient(58deg, rgba(120,110,90,.030) 0 1px, transparent 1px 7px),
    repeating-linear-gradient(-31deg, rgba(120,110,90,.022) 0 1px, transparent 1px 11px),
    radial-gradient(120% 90% at 50% -10%, rgba(255,255,255,.55), transparent 60%);}
::selection{background:rgba(232,122,144,.22)}
.progress{position:fixed;top:0;left:0;height:2px;width:0;z-index:60;
  background:linear-gradient(90deg,var(--ai),var(--sakura));transition:width .1s linear}

/* 页眉 */
header.hero{padding:clamp(64px,11vh,112px) 28px clamp(28px,5vh,46px);text-align:center}
header.hero .mark{width:1px;height:40px;margin:0 auto 24px;
  background:linear-gradient(180deg,transparent,var(--muted-2))}
h1.title{font-family:var(--serif);font-weight:600;font-size:clamp(42px,9vw,66px);
  line-height:1;letter-spacing:.3em;margin:0 0 0 .3em;color:var(--ink)}
header.hero .sub{font-family:var(--serif);font-size:13px;letter-spacing:.42em;color:var(--muted);
  margin:24px 0 0 .42em}
header.hero .meta{font-family:var(--sans);font-size:11.5px;letter-spacing:.2em;color:var(--muted-2);
  margin-top:20px}
header.hero .meta b{font-weight:500;color:var(--muted)}
header.hero .dot{display:inline-block;width:4px;height:4px;border-radius:50%;
  background:var(--sakura);vertical-align:middle;margin:0 9px;opacity:.75}

/* 专辑切换 */
nav.tabs{display:flex;justify-content:center;gap:6px;flex-wrap:wrap;
  padding:0 20px clamp(30px,6vh,50px);font-family:var(--sans)}
nav.tabs button{
  appearance:none;background:none;border:none;cursor:pointer;
  font-family:var(--serif);font-size:15px;letter-spacing:.12em;color:var(--muted);
  padding:9px 16px 11px;border-bottom:1px solid transparent;
  transition:color .2s,border-color .2s}
nav.tabs button:hover{color:var(--ink-soft)}
nav.tabs button.on{color:var(--ink);border-bottom-color:var(--acc)}
nav.tabs button .cn{opacity:.62;font-size:13px;margin-left:.5em}

/* 网格 */
.wrap{max-width:820px;margin:0 auto;padding:0 clamp(20px,5vw,52px);
  display:grid;grid-template-columns:220px minmax(0,1fr);gap:clamp(24px,4vw,52px);align-items:start}

/* 侧栏 */
aside.side{position:sticky;top:32px;font-family:var(--sans);padding-bottom:60px}
aside.side .album-en{font-family:var(--serif);font-size:19px;line-height:1.5;color:var(--ink);
  letter-spacing:.02em}
aside.side .album-cn{font-family:var(--serif);font-size:13.5px;color:var(--muted);margin-top:5px;
  letter-spacing:.14em}
aside.side .album-credit{font-size:10.5px;letter-spacing:.24em;color:var(--muted-2);
  margin-top:14px;padding-bottom:14px;border-bottom:1px solid var(--line)}
aside.side .album-note{font-size:10.5px;line-height:1.9;color:var(--muted-2);
  margin:12px 0 18px;letter-spacing:.02em}
aside.side .toc-h{font-size:10.5px;letter-spacing:.34em;color:var(--muted-2);margin-bottom:10px}
aside.side ol{list-style:none;margin:0;padding:0}
aside.side li{margin:0}
aside.side a{display:flex;gap:9px;align-items:baseline;text-decoration:none;color:var(--muted);
  padding:6px 10px 6px 12px;border-left:1px solid var(--line-soft);
  transition:color .18s,border-color .18s,background .18s}
aside.side a:hover{color:var(--ink);border-left-color:var(--muted-2);background:rgba(255,255,255,.5)}
aside.side a .n{font-size:10.5px;color:var(--muted-2);font-variant-numeric:tabular-nums;
  min-width:1.7em;transition:color .18s}
aside.side a .t{font-size:12.5px;line-height:1.6;font-family:var(--serif);
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
aside.side a .ins{font-size:9.5px;letter-spacing:.14em;color:var(--muted-2);
  border:1px solid var(--line);border-radius:2px;padding:0 4px;flex:0 0 auto}
aside.side a.on{color:var(--ink);border-left-color:var(--acc);background:rgba(255,255,255,.72)}
aside.side a.on .n{color:var(--acc)}

/* 正文 */
main{padding-bottom:clamp(70px,14vh,130px);min-width:0}
.album{display:none}
.album.on{display:block}
.song{padding:0 0 clamp(48px,8vh,78px);scroll-margin-top:38px}
.song + .song{border-top:1px solid var(--line-soft);padding-top:clamp(48px,8vh,78px)}
.song-head{display:flex;align-items:baseline;gap:14px;margin-bottom:24px;flex-wrap:wrap}
.song-head .no{font-family:var(--serif);font-size:clamp(24px,4.6vw,32px);line-height:1;
  color:var(--acc);opacity:.42;font-variant-numeric:tabular-nums;letter-spacing:.02em}
.song-head h3{margin:0;font-family:var(--serif);font-weight:600;font-size:clamp(20px,3.4vw,24px);
  line-height:1.45;letter-spacing:.04em;color:var(--ink)}
.song-head h3 .en{font-size:.82em;font-weight:500;letter-spacing:.03em}
.song-head h3 .cn{font-size:.72em;color:var(--muted);letter-spacing:.14em;margin-left:.6em}
.song-head .tag{font-family:var(--sans);font-size:10px;letter-spacing:.2em;color:var(--muted);
  border:1px solid var(--line);border-radius:2px;padding:2px 7px;transform:translateY(-2px)}
.song-note{font-family:var(--sans);font-size:11.5px;letter-spacing:.06em;color:var(--muted-2);
  margin:-12px 0 20px}
.instr{font-family:var(--sans);font-size:12px;letter-spacing:.16em;color:var(--muted-2);
  padding:2px 0 0}
.lyr{max-width:var(--lyr)}
.lyr p{margin:0;color:var(--ink-soft);font-size:18.5px;line-height:2.0}
.lyr .l{padding-left:0}
.lyr .pair{margin:0 0 1.3em}
.lyr .pair:last-child{margin-bottom:0}
.lyr .pair .en{color:var(--ink);font-family:var(--serif);font-size:18px;line-height:1.85;
  letter-spacing:.01em}
.lyr .pair .cn{color:var(--muted);font-size:15.5px;line-height:1.7;padding-left:1.1em}
.lyr .line + .line{margin-top:0}
footer{border-top:1px solid var(--line);padding:40px 28px 54px;text-align:center;font-family:var(--sans)}
footer .cr{display:block;font-size:11.5px;letter-spacing:.16em;color:var(--muted)}
footer .en{display:block;margin-top:10px;font-size:10px;letter-spacing:.22em;color:var(--muted-2)}
footer .en + .en{margin-top:6px}

@media (max-width:1000px){
  .wrap{grid-template-columns:minmax(0,1fr)}
  aside.side{position:static;top:auto;max-height:44vh;overflow:auto;
    border:1px solid var(--line);border-radius:3px;padding:16px 14px 10px;
    background:rgba(255,255,255,.42);margin-bottom:clamp(32px,7vh,52px)}
}
@media (max-width:560px){
  body{font-size:16px;line-height:1.95}
  h1.title{letter-spacing:.24em;margin-left:.24em}
  header.hero .sub{letter-spacing:.3em;margin-left:.3em;font-size:12px}
  .lyr .pair .cn{padding-left:.8em;font-size:14px}
  .song-head .no{font-size:22px}
}
"""

FAVICON = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E"
           "%3Crect width='32' height='32' fill='%23F5F0E0'/%3E"
           "%3Ctext x='16' y='23' font-size='19' text-anchor='middle' fill='%232E2C27'"
           " font-family='Songti SC,serif'%3E%E8%AF%8D%3C/text%3E%3C/svg%3E")


def song_html(al, s):
    sid = f'{al["key"]}-{s["no"]}'
    t = f'<span class="en">{esc(s["en"])}</span>' if s["en"] else ""
    if s["cn"]:
        t += f'<span class="cn">{esc(s["cn"])}</span>'
    tag = '<span class="tag">器乐</span>' if s["instrumental"] else ""
    out = [f'      <section class="song" id="{sid}" data-no="{s["no"]}">',
           f'        <div class="song-head"><span class="no">{s["no"]:02d}</span>'
           f'<h3>{t or esc(s["title"])}</h3>{tag}</div>']
    if s["note"]:
        out.append(f'        <p class="song-note">{esc(s["note"])}</p>')
    if s["instrumental"]:
        out.append('        <p class="instr">器乐 · 无歌词</p>')
    else:
        body = []
        for b in s["blocks"]:
            if b["t"] == "pair":
                body.append(f'          <div class="pair"><p class="en">{esc(b["en"])}</p>'
                            f'<p class="cn">{esc(b["cn"])}</p></div>')
            else:
                body.append(f'          <p class="line">{esc(b["x"])}</p>')
        out.append('        <div class="lyr">\n' + "\n".join(body) + "\n        </div>")
    out.append("      </section>")
    return "\n".join(out)


def build():
    albums = []
    for meta in ALBUMS:
        path = os.path.join(SRC, meta["file"])
        if not os.path.exists(path):
            raise SystemExit(f"缺少源文件：{path}")
        albums.append(parse(path, meta))

    json.dump({"albums": albums}, open(os.path.join(HERE, "lyrics.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    n_tracks = sum(len(a["songs"]) for a in albums)
    n_lyr = sum(1 for a in albums for s in a["songs"] if not s["instrumental"])
    n_bi = sum(1 for a in albums for s in a["songs"] if s["bilingual"])

    tabs, sided, maind = [], [], []
    for i, al in enumerate(albums):
        on = " on" if i == 0 else ""
        cnspan = f'<span class="cn">{esc(al["cn"])}</span>' if al["cn"] else ""
        tabs.append(f'    <button type="button" data-album="{al["key"]}" class="{on.strip()}"'
                    f' style="--acc:{al["accent"]}">'
                    f'{esc(al["en"])}{cnspan}</button>')

        li = []
        for s in al["songs"]:
            mark = '<span class="ins">器乐</span>' if s["instrumental"] else ""
            label = s["en"] or s["cn"] or s["title"]
            if s["en"] and s["cn"]:
                label = f'{s["en"]} · {s["cn"]}'
            li.append(f'      <li><a href="#{al["key"]}-{s["no"]}">'
                      f'<span class="n">{s["no"]:02d}</span>'
                      f'<span class="t">{esc(label)}</span>{mark}</a></li>')
        sided.append(f'''    <div class="album-side" data-album="{al["key"]}"{"" if i == 0 else " hidden"}
      style="--acc:{al["accent"]};--acc-soft:{al["accent_soft"]}">
      <div class="album-en">{esc(al["en"])}</div>
      {f'<div class="album-cn">{esc(al["cn"])}</div>' if al["cn"] else ""}
      <div class="album-credit">词曲 AKITO LAU</div>
      {f'<div class="album-note">{esc(al["note"])}</div>' if al["note"] else ""}
      <div class="toc-h">曲目</div>
      <ol>
{chr(10).join(li)}
      </ol>
    </div>''')

        songs = "\n".join(song_html(al, s) for s in al["songs"])
        maind.append(f'    <div class="album{on}" data-album="{al["key"]}"\n'
                     f'      style="--acc:{al["accent"]};--acc-soft:{al["accent_soft"]}">\n'
                     f'{songs}\n    </div>')

    out = f"""<!DOCTYPE html>
<html lang="zh-Hans">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>歌词 · {CN_NUM.get(len(albums), len(albums))}张专辑</title>
<meta name="description" content="{' / '.join(a['en'] for a in albums)} —— {len(albums)} 张专辑的全部歌词，{n_tracks} 首曲目。">
<meta name="author" content="Akito Lau">
<meta name="theme-color" content="#F5F0E0">
<link rel="icon" href="{FAVICON}">
<style>{CSS}</style>
</head>
<body>
<div class="progress" id="prog"></div>

<header class="hero">
  <div class="mark"></div>
  <h1 class="title">歌词</h1>
  <div class="sub">{CN_NUM.get(len(albums), len(albums))}张专辑</div>
  <div class="meta">{n_tracks} 首曲目<span class="dot"></span>{n_lyr} 首有词<span class="dot"></span><b>Akito Lau</b></div>
</header>

<nav class="tabs" id="tabs">
{chr(10).join(tabs)}
</nav>

<div class="wrap">

  <aside class="side" id="side">
{chr(10).join(sided)}
  </aside>

  <main id="main">
{chr(10).join(maind)}
  </main>
</div>

<footer>
  <span class="cr">© <span id="yr">{datetime.date.today().year}</span> Akito Lau 版权所有</span>
  <span class="en">ALL RIGHTS RESERVED</span>
  <span class="en">未经许可，请勿转载</span>
</footer>

<script>
(function(){{
  document.getElementById('yr').textContent = new Date().getFullYear();

  /* 专辑切换 */
  var tabs = [].slice.call(document.querySelectorAll('#tabs button'));
  function activate(key){{
    tabs.forEach(function(b){{ b.classList.toggle('on', b.dataset.album === key); }});
    document.querySelectorAll('#main .album').forEach(function(el){{
      el.classList.toggle('on', el.dataset.album === key); }});
    document.querySelectorAll('#side .album-side').forEach(function(el){{
      el.hidden = (el.dataset.album !== key); }});
    window.scrollTo({{top:0, behavior:'instant' in window ? 'instant' : 'auto'}});
    recon(); progress();
  }}
  tabs.forEach(function(b){{ b.addEventListener('click', function(){{ activate(b.dataset.album); }}); }});

  /* 阅读进度 */
  var prog = document.getElementById('prog'), raf = false;
  function progress(){{
    var h = document.documentElement.scrollHeight - window.innerHeight;
    prog.style.width = (h > 0 ? Math.min(100, (window.scrollY / h) * 100) : 0) + '%';
    raf = false;
  }}
  window.addEventListener('scroll', function(){{ if(!raf){{ raf = true; requestAnimationFrame(progress); }} }}, {{passive:true}});
  window.addEventListener('resize', progress);

  /* 目录高亮（只观察当前专辑的曲目） */
  var io = null, vis = {{}};
  function recon(){{
    if(io) io.disconnect();
    vis = {{}};
    var active = document.querySelector('#main .album.on');
    if(!active || !('IntersectionObserver' in window)) return;
    var links = [].slice.call(document.querySelectorAll('#side .album-side:not([hidden]) a'));
    var map = {{}};
    links.forEach(function(a){{ map[a.getAttribute('href').slice(1)] = a; }});
    io = new IntersectionObserver(function(es){{
      es.forEach(function(e){{ vis[e.target.id] = e.isIntersecting ? e.intersectionRatio : 0; }});
      var best = null, bv = 0;
      for(var k in vis){{ if(vis[k] > bv){{ bv = vis[k]; best = k; }} }}
      if(best){{ links.forEach(function(a){{ a.classList.remove('on'); }});
        if(map[best]) map[best].classList.add('on'); }}
    }}, {{rootMargin:'-10% 0px -60% 0px', threshold:[0,.12,.35,.6,1]}});
    [].slice.call(active.querySelectorAll('section.song')).forEach(function(s){{ io.observe(s); }});
  }}
  recon(); progress();
}})();
</script>
</body>
</html>
"""
    open(os.path.join(HERE, "index.html"), "w", encoding="utf-8").write(out)
    print(f"生成 index.html：{len(albums)} 张专辑 / {n_tracks} 首曲目"
          f"（{n_lyr} 首有词，双语对照 {n_bi} 首），{len(out)} 字节")
    if WARN:
        print(f"\n⚠️ 需要确认 {len(WARN)} 项：")
        for w in WARN:
            print(f"   · {w}")
    print(f"机械修正 {len(MODS)} 处：")
    for a, b in MODS:
        print(f"   「{a}」 → 「{b}」")


if __name__ == "__main__":
    build()
