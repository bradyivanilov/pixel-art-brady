"""Kartu Sosmed - ubah hasil produksi kantor finance jadi gambar 1:1 + caption.

Ambil inti (ringkasan) dan perspektif (sudut pandang pembeda dari analis),
lalu render jadi kartu 1080x1080 lewat Chrome headless, plus caption siap
pakai untuk TikTok dan Instagram.

Pakai:
    python kartu.py                # edisi terbaru
    python kartu.py --id 20261002-190756
"""
from __future__ import annotations

import argparse
import html
import json
import re
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent
OUT = BASE / "output"
TMP = Path(tempfile.gettempdir())


def _chrome_path() -> Path | None:
    """Cari Chrome di lokasi umum (Windows/macOS/Linux)."""
    kandidat = [
        Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
        Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
        Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
        Path("/usr/bin/google-chrome"),
        Path("/usr/bin/chromium"),
        Path("/usr/bin/chromium-browser"),
    ]
    for p in kandidat:
        if p.exists():
            return p
    import shutil
    for nama in ("chrome", "google-chrome", "chromium", "chromium-browser"):
        p = shutil.which(nama)
        if p:
            return Path(p)
    return None


CHROME = _chrome_path()

WILAYAH_LABEL = {
    "indonesia": "INDONESIA", "global": "GLOBAL", "asean": "ASEAN",
    "eropa": "EROPA", "amerika": "AMERIKA", "arab": "TIMUR TENGAH",
}


def edisi_terbaru() -> Path:
    kandidat = sorted(OUT.glob("berita-*.json"), key=lambda p: p.stat().st_mtime)
    if not kandidat:
        raise SystemExit("Belum ada output berita-*.json di folder output/.")
    return kandidat[-1]


def _bagian(teks: str, judul: str) -> str:
    """Ambil isi di bawah heading '## judul' sampai heading berikutnya."""
    m = re.search(rf"(?im)^#{{1,3}}\s*{re.escape(judul)}.*?$", teks or "")
    if not m:
        return ""
    sisa = teks[m.end():]
    n = re.search(r"(?m)^#{1,3}\s", sisa)
    isi = sisa[:n.start()] if n else sisa
    isi = re.sub(r"[*_`>|]", "", isi)
    isi = re.sub(r"^\s*[-•]\s*", "", isi, flags=re.M)
    isi = re.sub(r"\n{2,}", "\n", isi)
    return isi.strip()


def _rapikan(teks: str, maks: int) -> str:
    teks = re.sub(r"\s+", " ", (teks or "").strip())
    if len(teks) <= maks:
        return teks
    potong = teks[:maks]
    titik = potong.rfind(". ")
    if titik > maks * 0.55:
        return potong[:titik + 1]
    return potong.rstrip(" ,;:") + "…"


def _ambil_angka(analis: str) -> str:
    """Cari satu angka/figur kunci yang menonjol dari analisis."""
    m = re.search(r"\*\*(\d[\d.,]*\s*(?:persen|%)?)\*\*", analis or "")
    if m:
        return m.group(1).strip()
    m = re.search(r"(\d[\d.,]*\s*(?:persen|%))", analis or "")
    return m.group(1).strip() if m else ""


def ekstrak(data: dict) -> dict:
    hasil = data.get("hasil", {})
    analis = hasil.get("analis", "")
    inti = _rapikan(data.get("ringkasan", ""), 260)
    perspektif = _rapikan(_bagian(analis, "Sudut Pandang Pembeda"), 260)
    if not perspektif:
        perspektif = _rapikan(_bagian(analis, "Penyebab Utama"), 260)
    headline0 = (data.get("headline") or [{}])[0]
    return {
        "id": data.get("run_id", ""),
        "waktu": data.get("waktu", ""),
        "judul": data.get("judul_final", data.get("topik", "")),
        "inti": inti,
        "perspektif": perspektif,
        "angka": _ambil_angka(analis),
        "tagar": data.get("tagar", ""),
        "disclaimer": data.get("disclaimer", ""),
        "wilayah": WILAYAH_LABEL.get(headline0.get("wilayah", ""), "INDONESIA"),
        "sumber": headline0.get("sumber", ""),
    }


TEMPLATE = """<!doctype html>
<html lang="id"><head><meta charset="utf-8">
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  html,body { width:1080px; height:1080px; overflow:hidden; }
  body {
    font-family:"Segoe UI","Inter",Arial,sans-serif;
    background:#0c1729;
    background-image:radial-gradient(circle at 88% -8%, #1d3a63 0%, transparent 46%),
                     radial-gradient(circle at -6% 108%, #123047 0%, transparent 44%);
    color:#eaf0f7; padding:56px 60px; display:flex; flex-direction:column;
  }
  .top { display:flex; justify-content:space-between; align-items:center; }
  .brand { display:flex; align-items:center; gap:14px; }
  .brand .dot { width:20px; height:20px; border-radius:6px;
    background:linear-gradient(135deg,#f5b32c,#e8891b); box-shadow:0 0 18px #e8891b80; }
  .brand .nm { font-size:23px; font-weight:800; letter-spacing:.5px; }
  .brand .nm span { color:#f5b32c; }
  .meta { display:flex; gap:12px; align-items:center; }
  .pill { font-size:19px; font-weight:700; padding:7px 18px; border-radius:999px;
    background:#f5b32c; color:#20160a; letter-spacing:.6px; }
  .tgl { font-size:19px; color:#93a6c0; font-weight:600; }
  h1 { margin-top:34px; font-size:{FS}px; line-height:1.13; font-weight:800;
       letter-spacing:-.5px; overflow:hidden; }
  h1 .hl { color:#f5b32c; }
  .angka { margin-top:24px; display:flex; align-items:baseline; gap:20px; }
  .angka b { font-size:84px; font-weight:900; color:#4fd1c5; line-height:1;
             letter-spacing:-2px; }
  .angka i { font-style:normal; font-size:25px; color:#9fb3cc; font-weight:600;
             max-width:540px; }
  .blok { margin-top:auto; display:flex; flex-direction:column; gap:18px; }
  .box { background:#12233c; border-radius:20px; padding:22px 28px 22px 30px;
         border-left:9px solid #f5b32c; }
  .box.p { border-left-color:#4fd1c5; }
  .box .lbl { font-size:18px; font-weight:800; letter-spacing:2.4px;
              color:#f5b32c; margin-bottom:9px; }
  .box.p .lbl { color:#4fd1c5; }
  .box .tx { font-size:27px; line-height:1.4; color:#e9f0f8; font-weight:500; }
  .foot { margin-top:28px; display:flex; justify-content:space-between;
          align-items:flex-end; }
  .tag { font-size:22px; color:#f5b32c; font-weight:700; max-width:700px;
         line-height:1.5; }
  .src { font-size:19px; color:#8296b1; text-align:right; font-weight:600; }
</style></head><body>
  <div class="top">
    <div class="brand"><div class="dot"></div>
      <div class="nm">KANTOR BERITA <span>FINANCE</span></div></div>
    <div class="meta"><div class="pill">{WILAYAH}</div>
      <div class="tgl">{WAKTU}</div></div>
  </div>
  <h1>{JUDUL}</h1>
  {ANGKA_BLOK}
  <div class="blok">
    <div class="box"><div class="lbl">INTI</div><div class="tx">{INTI}</div></div>
    <div class="box p"><div class="lbl">PERSPEKTIF</div><div class="tx">{PERSPEKTIF}</div></div>
  </div>
  <div class="foot">
    <div class="tag">{TAGAR}</div>
    <div class="src">Sumber: {SUMBER}</div>
  </div>
</body></html>"""


def render_html(k: dict) -> str:
    angka_blok = ""
    if k["angka"]:
        angka_blok = (f'<div class="angka"><b>{html.escape(k["angka"])}</b>'
                      f'<i>angka kunci dari bahan sumber</i></div>')
    judul = k["judul"]
    # judul panjang -> huruf mengecil biar tetap utuh, tidak terpotong
    if len(judul) <= 58:
        fs = 62
    elif len(judul) <= 80:
        fs = 54
    elif len(judul) <= 105:
        fs = 47
    else:
        fs = 41
    isi = {
        "WILAYAH": html.escape(k["wilayah"]),
        "WAKTU": html.escape(k["waktu"].replace(" WIB", "")),
        "JUDUL": html.escape(judul),
        "FS": str(fs),
        "INTI": html.escape(k["inti"]),
        "PERSPEKTIF": html.escape(k["perspektif"]),
        "TAGAR": html.escape(k["tagar"]),
        "SUMBER": html.escape(k["sumber"]),
        "ANGKA_BLOK": angka_blok,
    }
    out = TEMPLATE
    for a, b in isi.items():
        out = out.replace("{" + a + "}", b)
    return out


def potret(html_path: Path, png_path: Path) -> bool:
    if CHROME is None:
        print("Chrome/Chromium tidak ditemukan — tidak bisa render PNG.")
        return False
    cmd = [
        str(CHROME), "--headless=new", "--disable-gpu", "--hide-scrollbars",
        "--force-device-scale-factor=1", "--window-size=1080,1080",
        "--default-background-color=00000000",
        f"--screenshot={png_path}", html_path.as_uri(),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
    return png_path.exists() and png_path.stat().st_size > 2000


def caption(k: dict) -> str:
    tagar = k["tagar"] or ""
    tagar_tiktok = tagar + " #fyp #berita #ekonomi #news #update"
    tagar_ig = tagar + " #beritaekonomi #kabarekbisnis"
    sumber = k["sumber"]
    return f"""============================================================
CAPTION SOSMED - {k['judul']}
Edisi {k['id']} | {k['waktu']}
============================================================

------------------------------------------------------------
VERSI TIKTOK (hook 3 detik pertama, gaya santai)
------------------------------------------------------------
{k['judul']}

{k['inti']}

Yang bikin beda: {k['perspektif']}

Sumber: {sumber}. Data yang belum ada kami tulis apa adanya, bukan dikarang.

Ikuti buat update ekonomi tiap hari.
{tagar_tiktok}

------------------------------------------------------------
VERSI INSTAGRAM (caption rapi, siap feed)
------------------------------------------------------------
{k['judul']}

{k['inti']}

Sudut pandang kami: {k['perspektif']}

Sumber: {sumber}
{k['disclaimer']}

Simpan postingan ini biar nggak ketinggalan update berikutnya.
{tagar_ig}

------------------------------------------------------------
TEKS DI DALAM GAMBAR (sudah terpasang di kartu 1080x1080)
------------------------------------------------------------
Label wilayah : {k['wilayah']}
Judul         : {k['judul']}
Inti          : {k['inti']}
Perspektif    : {k['perspektif']}
{('Angka kunci   : ' + k['angka']) if k['angka'] else ''}

------------------------------------------------------------
CATATAN PEMAKAIAN
------------------------------------------------------------
- Gambar: kartu-kartu/kartu-{k['id']}.png (1080x1080, aman untuk TikTok & IG).
- TikTok: pakai VERSI TIKTOK, taruh 1-2 kalimat pertama sebagai teks di video.
- Instagram: pakai VERSI INSTAGRAM untuk caption feed atau Reels.
- Jangan ubah angka dan kutipan; semuanya sudah lewat verifikasi.
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", default=None, help="run_id edisi, default terbaru")
    args = ap.parse_args()

    if args.id:
        j = OUT / f"berita-{args.id}.json"
        if not j.exists():
            raise SystemExit(f"Tidak ada {j.name}")
    else:
        j = edisi_terbaru()

    data = json.loads(j.read_text(encoding="utf-8"))
    k = ekstrak(data)
    k["id"] = k["id"] or j.stem.replace("berita-", "")

    kartu_dir = BASE / "kartu-kartu"
    kartu_dir.mkdir(exist_ok=True)
    html_tmp = TMP / f"_kartu_{k['id']}.html"
    png = kartu_dir / f"kartu-{k['id']}.png"

    html_tmp.write_text(render_html(k), encoding="utf-8")
    ok = potret(html_tmp, png)
    cap_path = kartu_dir / f"caption-{k['id']}.txt"
    cap_path.write_text(caption(k), encoding="utf-8")

    print(f"edisi      : {k['id']}")
    print(f"judul      : {k['judul']}")
    print(f"wilayah    : {k['wilayah']} | sumber: {k['sumber']}")
    print(f"angka kunci: {k['angka'] or '-'}")
    print(f"gambar     : {png} ({png.stat().st_size if png.exists() else 0} bytes) {'OK' if ok else 'GAGAL'}")
    print(f"caption    : {cap_path}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
