#!/usr/bin/env python3
"""Render a vertical 1080x1350 cover for the KMA Telegram channel.

Usage:
  python3 tools/render_cover.py spec.json covers/2026-10-30-slug.jpg

spec.json fields (all strings unless noted):
  layout    "stat" (default) or "score"
  accent    "games" | "esports" | "giveaway" | a hex colour like "#FFC22E"
  category  top-right label, e.g. "Игры" or "Киберспорт"
  date      optional, defaults to today's date in Moscow (DD.MM.YYYY)
  chip      small label above the title, e.g. "Релиз дня" or "CS2 · IEM Beijing"
  title     headline; use \n for line breaks; auto-shrinks to fit

  layout "stat":
    big     the large accent number/phrase, e.g. "430 000+" or "0 ₽"
    cap     caption under the big number; may contain <b>bold</b>
    cards   optional list (max 3) of {"b": "88", "s": "Metacritic"}
    bar     optional {"left": "сегодня · 20:00 мск", "right": "Spirit - NAVI"}

  layout "score":
    team1, score1, team2, score2   (winner = higher score, shown in accent)
    maps    optional list (max 3) of {"name": "NUKE", "score": "13 : 11", "win": true}
    bar     optional {"left": "...", "right": "..."}
"""
import base64
import datetime as dt
import html
import json
import os
import sys

from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W, H = 1080, 1350
ACCENTS = {"games": "#FFC22E", "esports": "#2EC4B6", "giveaway": "#FF7A1A"}


def esc(s):
    return html.escape(str(s or ""), quote=True)


def rich(s):
    """Escape, then allow <b>…</b> and line breaks (\\n or <br>) back in."""
    out = esc(s).replace("&lt;b&gt;", "<b>").replace("&lt;/b&gt;", "</b>")
    return out.replace("&lt;br&gt;", "<br>").replace("\n", "<br>")


def build(spec):
    accent = ACCENTS.get(spec.get("accent", "games"), spec.get("accent", "#FFC22E"))
    msk = dt.timezone(dt.timedelta(hours=3))
    date = spec.get("date") or dt.datetime.now(msk).strftime("%d.%m.%Y")
    logo = "data:image/png;base64," + base64.b64encode(
        open(os.path.join(ROOT, "assets", "kma_logo.png"), "rb").read()).decode()
    title = "<br>".join(esc(x) for x in str(spec.get("title", "")).split("\n"))
    layout = spec.get("layout", "stat")

    bar = spec.get("bar")
    bar_html = (f'<div class="bar"><span>{esc(bar.get("left"))}</span><b>{esc(bar.get("right"))}</b></div>'
                if bar else "")

    if layout == "score":
        s1, s2 = spec.get("score1", ""), spec.get("score2", "")
        try:
            w1, w2 = float(s1) > float(s2), float(s2) > float(s1)
        except ValueError:
            w1 = w2 = False
        maps = "".join(
            f'<div class="map {"w" if m.get("win") else "l"}"><span>{esc(m.get("name"))}</span>'
            f'<b>{esc(m.get("score"))}</b></div>' for m in (spec.get("maps") or [])[:3])
        body = f"""
<div class="board">
 <div class="row"><span class="team{'' if w1 or not w2 else ' lose'}">{esc(spec.get('team1'))}</span><span class="n{' win' if w1 else ''}">{esc(s1)}</span></div>
 <div class="row"><span class="team{'' if w2 or not w1 else ' lose'}">{esc(spec.get('team2'))}</span><span class="n{' win' if w2 else ''}">{esc(s2)}</span></div>
 {f'<div class="maps">{maps}</div>' if maps else ''}
</div>"""
    else:
        cards = "".join(f'<div class="card"><b>{esc(c.get("b"))}</b><span>{esc(c.get("s"))}</span></div>'
                        for c in (spec.get("cards") or [])[:3])
        body = f"""
<div class="stat"><div class="big">{esc(spec.get('big'))}</div><div class="cap">{rich(spec.get('cap'))}</div></div>
{f'<div class="cards">{cards}</div>' if cards else ''}"""

    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
*{{margin:0;padding:0;box-sizing:border-box}}
:root{{--a:{accent}}}
html,body{{width:{W}px;height:{H}px;overflow:hidden}}
body{{background:#0A0A10;color:#F4F4F8;font-family:'Inter','Inter Display','DejaVu Sans',sans-serif;position:relative}}
.grid{{position:absolute;inset:0;background-image:linear-gradient(rgba(255,255,255,.035) 1px,transparent 1px),
  linear-gradient(90deg,rgba(255,255,255,.035) 1px,transparent 1px);background-size:45px 45px}}
.glow{{position:absolute;width:1000px;height:1000px;border-radius:50%;filter:blur(140px);opacity:.26;background:var(--a);right:-520px;top:420px}}
.slash{{position:absolute;right:-300px;top:0;width:560px;height:100%;background:var(--a);opacity:.08;transform:skewX(-14deg)}}
.logo{{position:absolute;left:52px;top:40px;height:190px}}
.meta{{position:absolute;right:72px;top:80px;text-align:right;color:#9A9AAE;font-weight:600;font-size:24px;line-height:1.45}}
.meta b{{color:#F4F4F8;font-weight:800;display:block;font-size:26px}}
.top{{position:absolute;left:72px;right:72px;top:290px}}
.chip{{display:inline-block;color:#0A0A10;background:var(--a);font-weight:800;font-size:24px;letter-spacing:.08em;
  padding:11px 18px;border-radius:8px;text-transform:uppercase;max-width:100%;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.h1{{font-family:'Inter Display','Inter',sans-serif;font-weight:900;text-transform:uppercase;line-height:.93;
  letter-spacing:-.02em;margin-top:26px;font-size:150px}}
.mid{{position:absolute;left:72px;right:72px;bottom:120px;display:flex;flex-direction:column;gap:22px}}
.big{{font-family:'Inter Display','Inter',sans-serif;font-weight:900;line-height:.85;color:var(--a);letter-spacing:-.03em;
  font-variant-numeric:tabular-nums;font-size:150px;white-space:nowrap}}
.cap{{font-size:30px;font-weight:600;color:#C9C9D6;line-height:1.3;margin-top:16px}}
.cap b{{color:#F4F4F8}}
.cards{{display:flex;gap:14px}}
.card{{flex:1;background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.13);border-radius:18px;padding:22px 24px}}
.card b{{display:block;font-family:'Inter Display','Inter',sans-serif;font-weight:900;font-size:46px;line-height:1;white-space:nowrap}}
.card span{{display:block;color:#9A9AAE;font-weight:600;font-size:20px;margin-top:10px}}
.row{{display:flex;justify-content:space-between;align-items:center;padding:16px 28px;border-radius:18px;
  background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.1);margin-bottom:12px}}
.team{{font-family:'Inter Display','Inter',sans-serif;font-weight:900;font-size:68px;letter-spacing:-.01em;text-transform:uppercase}}
.team.lose{{color:#6E6E84}}
.n{{font-family:'Inter Display','Inter',sans-serif;font-weight:900;font-size:80px;line-height:1;color:#6E6E84}}
.n.win{{color:var(--a)}}
.maps{{display:flex;gap:12px}}
.map{{flex:1;display:flex;flex-direction:column;gap:6px;font-weight:700;font-size:20px;color:#9A9AAE;
  background:rgba(255,255,255,.04);border-radius:14px;padding:14px 18px;letter-spacing:.04em}}
.map b{{font-size:34px;font-variant-numeric:tabular-nums;color:#F4F4F8;letter-spacing:0}}
.map.w b{{color:var(--a)}} .map.l b{{color:#6E6E84}}
.bar{{display:flex;justify-content:space-between;align-items:center;gap:20px;background:var(--a);color:#0A0A10;
  border-radius:18px;padding:22px 28px;font-weight:700;font-size:26px}}
.bar b{{font-family:'Inter Display','Inter',sans-serif;font-weight:900;font-size:38px;text-align:right}}
.foot{{position:absolute;left:72px;right:72px;bottom:52px;display:flex;justify-content:space-between;
  color:#6E6E84;font-weight:600;font-size:22px;letter-spacing:.03em}}
</style></head><body>
<div class="grid"></div><div class="glow"></div><div class="slash"></div>
<img class="logo" src="{logo}">
<div class="meta"><b>{esc(spec.get('category', 'Игры'))}</b>{esc(date)}</div>
<div class="top"><span class="chip">{esc(spec.get('chip'))}</span><div class="h1" id="h1">{title}</div></div>
<div class="mid" id="mid">{body}{bar_html}</div>
<div class="foot"><span>t.me/esportsmedicine</span><span>КМА · игры и киберспорт</span></div>
</body></html>"""


FIT_JS = """() => {
  const h1 = document.getElementById('h1'), mid = document.getElementById('mid');
  const big = document.querySelector('.big');
  // shrink the big number until it fits the width
  if (big) { let s = 150; while (big.scrollWidth > 936 && s > 60) { s -= 4; big.style.fontSize = s + 'px'; } }
  // shrink cards' numbers if they overflow
  document.querySelectorAll('.card b').forEach(b => { let s = 46; while (b.scrollWidth > b.parentElement.clientWidth - 48 && s > 24) { s -= 2; b.style.fontSize = s + 'px'; } });
  // headline must fit between the chip and the middle block, and within the width
  const limit = () => mid.getBoundingClientRect().top - 40;
  let size = 150;
  while (size > 56 && (h1.getBoundingClientRect().bottom > limit() || h1.scrollWidth > 936)) {
    size -= 4; h1.style.fontSize = size + 'px';
  }
  return size;
}"""


def main():
    spec_path, out = sys.argv[1], sys.argv[2]
    spec = json.load(open(spec_path, encoding="utf-8"))
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    png = out[:-4] + ".png" if out.lower().endswith((".jpg", ".jpeg")) else out
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": W, "height": H})
        pg.set_content(build(spec))
        pg.evaluate("document.fonts.ready")
        size = pg.evaluate(FIT_JS)
        pg.screenshot(path=png)
        b.close()
    if png != out:
        from PIL import Image
        Image.open(png).convert("RGB").save(out, quality=88, optimize=True, progressive=True)
        os.remove(png)
    print(f"wrote {out} (title {size}px)")


if __name__ == "__main__":
    main()
