#!/usr/bin/env python3
"""Kantor Berita Finance - mesin produksi berita.

Alur kerja (mirip ruang redaksi sungguhan):
  riset -> analis -> penulis -> editor -> verifikator -> penerbit

Tiap pekerja adalah satu panggilan model ke 9router (OpenAI-compatible).
Hasil tiap tahap dioper ke tahap berikutnya.

INPUT yang rapi:
  - banyak feed berita di config.json, tahan gagal satu per satu
  - tiap headline ditarik ISI ARTIKELNYA, bukan cuma judul
  - bahan sumber (isi artikel) dioper ke analis, penulis, dan verifikator
  - memori redaksi: topik yang sudah pernah terbit tidak dipilih lagi

OUTPUT yang rapi, tiga berkas per edisi:
  - berita-<id>.md    : artikel bersih siap dibaca/tayang (judul, lead, isi,
                        tagar, disclaimer, sumber). Tidak ada instruksi internal.
  - catatan-<id>.md   : catatan proses redaksi untuk audit (riset, analisis,
                        verifikasi). Terpisah supaya tidak mengotori artikel.
  - berita-<id>.json  : data mentah lengkap semua tahap + headline + sumber.

Jalankan:
  python engine.py                 # produksi satu berita
  python engine.py --topik "..."   # paksa topik tertentu
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from roles import ROLES, BY_ID  # noqa: E402

WIB = timezone(timedelta(hours=7))
CFG = json.loads((HERE / "config.json").read_text(encoding="utf-8"))
OUT_DIR = HERE / CFG["output_dir"]
STATUS_FILE = HERE / "status.json"
LOG_FILE = HERE / "kantor.log"
ARSIP_FILE = HERE / "arsip.json"

API_BASE = "http://localhost:20128/v1"
API_KEY_ENV = "HERMES_CUSTOM_LOCALHOST_20128_API_KEY"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

# potongan teks sampah yang sering nempel di halaman berita
JUNK = re.compile(
    r"(?i)(cookie|javascript|aktifkan|baca juga|lihat juga|iklan|advertisement|"
    r"subscribe|newsletter|tautan telah disalin|url telah tercopy|share|komentar|"
    r"loading|major indexes|indo-fx|usd-fx|dapatkan informasi|unduh aplikasi|"
    r"follow us|syarat dan ketentuan|kebijakan privasi|all rights reserved)")

STOP = {"yang", "dan", "untuk", "dengan", "dari", "pada", "ini", "itu", "akan",
        "tidak", "adalah", "juga", "bisa", "dalam", "ke", "di", "atau", "the",
        "of", "to", "and", "in", "for", "a", "an", "hari", "tahun", "saat"}

# kata kunci bisnis/ekonomi, dipakai menyaring feed berita umum
BISNIS = re.compile(
    r"(?i)(ekonomi|ekonom|bisnis|business|market|pasar|saham|stock|investasi|invest|"
    r"keuangan|finance|financial|bank|rupiah|dollar|dolar|inflasi|inflation|pdb|gdp|"
    r"ekspor|impor|export|import|perdagangan|trade|harga|price|pajak|tax|utang|debt|"
    r"apbn|anggaran|budget|perusahaan|company|corporate|industri|industry|energi|energy|"
    r"minyak|oil|gas|batubara|coal|harga emas|gold price|suku bunga|interest rate|the fed|fed|"
    r"pertumbuhan|growth|investor|modal|capital|startup|umkm|kredit|credit|asuransi|"
    r"insurance|properti|property|manufaktur|manufactur|pengangguran|unemploy|upah|wage|"
    r"subsidi|subsid|tarif|tariff|neraca|deficit|surplus|ipo|merger|akuisisi|acquisition|"
    r"obligasi|bond|reksa|fund|emiten|listing|profit|rugi|revenue|pendapatan|konsumen|"
    r"consumer|ritel|retail|ecommerce|digital|teknologi|technology|ai\b|chip|semikonduktor)")


def log(msg: str) -> None:
    line = f"[{datetime.now(WIB).strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def read_api_key() -> str:
    import os
    if os.environ.get(API_KEY_ENV):
        return os.environ[API_KEY_ENV]
    for p in (Path.home() / "AppData" / "Local" / "hermes" / ".env",
              Path.home() / ".hermes" / ".env"):
        if p.is_file():
            for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = line.strip()
                if line.startswith(API_KEY_ENV):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit(f"{API_KEY_ENV} tidak ditemukan di .env Hermes")


def call_model(model: str, system: str, user: str, max_tokens: int = 1500,
               retries: int = 3) -> str:
    """Panggil 9router, dukung balasan streaming maupun JSON biasa."""
    body = json.dumps({
        "model": model,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
        "max_tokens": max_tokens,
        "stream": True,
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{API_BASE}/chat/completions", data=body,
        headers={"Content-Type": "application/json",
                 "Authorization": "Bearer " + read_api_key()})

    last_err = None
    for attempt in range(retries):
        try:
            out: list[str] = []
            with urllib.request.urlopen(req, timeout=240) as r:
                for raw in r:
                    s = raw.decode("utf-8", "ignore").strip()
                    if not s.startswith("data:"):
                        continue
                    payload = s[5:].strip()
                    if payload == "[DONE]":
                        break
                    try:
                        d = json.loads(payload)
                        delta = d["choices"][0].get("delta", {}).get("content")
                        if delta:
                            out.append(delta)
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue
            text = "".join(out).strip()
            if text:
                return text
            last_err = "balasan kosong"
        except Exception as e:  # noqa: BLE001
            last_err = f"{type(e).__name__}: {e}"
        time.sleep(2 + attempt * 3)
    raise RuntimeError(f"model {model} gagal: {last_err}")


# ---------------------------------------------------------------- input: feed

def _bersih_teks(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s)
    for a, b in (("&nbsp;", " "), ("&amp;", "&"), ("&quot;", '"'), ("&#39;", "'"),
                 ("&ldquo;", '"'), ("&rdquo;", '"'), ("&lsquo;", "'"),
                 ("&rsquo;", "'"), ("&mdash;", "\u2014"), ("&ndash;", "\u2013")):
        s = s.replace(a, b)
    return re.sub(r"\s+", " ", s).strip()


def _fetch(url: str, timeout: int = 20) -> str:
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept-Language": "id-ID,id;q=0.9,en;q=0.8"})
    return urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8", "ignore")


def tarik_isi_artikel(url: str, maks: int = 2600) -> str:
    """Tarik isi teks artikel dari halaman berita. Kosong kalau gagal."""
    if not url:
        return ""
    try:
        html = _fetch(url)
    except Exception:  # noqa: BLE001
        return ""
    h = re.sub(r"(?is)<(script|style|nav|footer|header|aside|noscript|form|iframe)"
               r"[^>]*>.*?</\1>", " ", html)
    blok: list[str] = []
    for pat in (
        r'(?is)<div[^>]+class="[^"]*(?:detail_text|itp_bodycontent|read__content|'
        r'post-body|article-content|article__body|content-detail|detail__body|'
        r'text_article|article-body|story__content)[^"]*"[^>]*>(.*?)(?:</div>\s*){1,3}',
        r"(?is)<article[^>]*>(.*?)</article>",
    ):
        for b in re.findall(pat, h):
            ps = [_bersih_teks(p) for p in re.findall(r"(?is)<p[^>]*>(.*?)</p>", b)]
            ps = [p for p in ps if len(p) > 60 and not JUNK.search(p)]
            if ps:
                blok.append(" ".join(ps))
    if not blok:
        ps = [_bersih_teks(p) for p in re.findall(r"(?is)<p[^>]*>(.*?)</p>", h)]
        ps = [p for p in ps if len(p) > 70 and not JUNK.search(p)]
        if ps:
            blok.append(" ".join(ps))
    best = max(blok, key=len) if blok else ""
    return best[:maks].strip()


def _parse_waktu(s: str) -> float:
    try:
        return parsedate_to_datetime(s).timestamp()
    except Exception:  # noqa: BLE001
        return 0.0


def _satu_feed(feed: dict) -> list[dict]:
    """Ambil headline dari satu feed. Kosong kalau gagal."""
    out: list[dict] = []
    for percobaan in range(2):
        try:
            root = ET.fromstring(_fetch(feed["url"], timeout=10))
            entries = list(root.iter("item")) or list(root.iter("entry"))
            for it in entries:
                title = (it.findtext("title") or "").strip()
                link = (it.findtext("link") or "").strip()
                if not link:  # Atom: <link href="..."/>
                    el = it.find("link")
                    if el is not None:
                        link = (el.get("href") or "").strip()
                pub = (it.findtext("pubDate") or it.findtext("updated")
                       or it.findtext("published") or "").strip()
                desc = _bersih_teks(it.findtext("description") or
                                    it.findtext("summary") or "")
                if title and (not feed.get("umum") or BISNIS.search(title)):
                    out.append({"judul": title, "sumber": feed["nama"],
                                "wilayah": feed.get("wilayah", "indonesia"),
                                "tautan": link, "waktu": pub,
                                "waktu_ts": _parse_waktu(pub),
                                "ringkas": desc[:300]})
                if len(out) >= 40:
                    break
            log(f"feed ok {feed['nama']}: {len(out)} item")
            return out
        except Exception as e:  # noqa: BLE001
            if percobaan == 1:
                log(f"feed gagal {feed['nama']}: {type(e).__name__}")
    return out


def fetch_headlines(limit: int = 8) -> list[dict]:
    """Ambil headline terbaru dari semua feed paralel. Tahan gagal per feed."""
    from concurrent.futures import ThreadPoolExecutor
    items: list[dict] = []
    with ThreadPoolExecutor(max_workers=12) as ex:
        for hasil in ex.map(_satu_feed, CFG["feeds"]):
            items.extend(hasil)
    seen, uniq = set(), []
    for it in items:
        k = re.sub(r"\W+", "", it["judul"].lower())[:60]
        if k and k not in seen:
            seen.add(k)
            uniq.append(it)
    uniq.sort(key=lambda x: x["waktu_ts"], reverse=True)
    # seimbangkan wilayah: ambil bergiliran antar wilayah biar tidak didominasi Indonesia
    per_wilayah: dict[str, list[dict]] = {}
    for it in uniq:
        per_wilayah.setdefault(it.get("wilayah", "indonesia"), []).append(it)
    urutan = ["indonesia", "global", "asean", "eropa", "amerika", "arab"]
    urutan += [w for w in per_wilayah if w not in urutan]
    hasil: list[dict] = []
    i = 0
    while len(hasil) < limit:
        ada = False
        for w in urutan:
            grup = per_wilayah.get(w, [])
            if i < len(grup):
                hasil.append(grup[i])
                ada = True
                if len(hasil) >= limit:
                    break
        if not ada:
            break
        i += 1
    return hasil


# ---------------------------------------------------------------- memori redaksi

def _tok(s: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", s.lower())
            if len(w) > 3 and w not in STOP}


def mirip(a: str, b: str) -> float:
    ta, tb = _tok(a), _tok(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def muat_arsip() -> list[dict]:
    if ARSIP_FILE.is_file():
        try:
            return json.loads(ARSIP_FILE.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            return []
    return []


def simpan_arsip(topik: str, judul: str) -> None:
    arsip = muat_arsip()
    arsip.append({"waktu": datetime.now(WIB).strftime("%Y-%m-%d %H:%M"),
                  "topik": topik, "judul": judul})
    ARSIP_FILE.write_text(json.dumps(arsip[-200:], ensure_ascii=False, indent=2),
                          encoding="utf-8")


def _topik_pernah_dibahas(topik: str, arsip: list[dict]) -> bool:
    return any(mirip(topik, a.get("topik", "")) > 0.55 for a in arsip)


# ---------------------------------------------------------------- status

def write_status(state: dict) -> None:
    """Tulis status tiap pekerja supaya pixel office bisa menampilkannya."""
    payload = {
        "ok": True,
        "sumber": "kantor-finance",
        "diperbarui": time.time(),
        "run_id": state.get("run_id"),
        "tahap": state.get("tahap"),
        "topik": state.get("topik"),
        "selesai": state.get("selesai", False),
        "pekerja": [],
    }
    for role in ROLES:
        st = state["pekerja"].get(role["id"], {})
        payload["pekerja"].append({
            "id": role["id"], "nama": role["nama"], "jabatan": role["jabatan"],
            "room": role["room"], "meja": role["meja"], "warna": role["warna"],
            "model": role["model"], "tugas": role["tugas"], "jobdesc": role["jobdesc"],
            "status": st.get("status", "idle"),
            "aktivitas": st.get("aktivitas", ""),
            "mulai": st.get("mulai"), "durasi_s": st.get("durasi_s"),
        })
    STATUS_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                           encoding="utf-8")


def set_status(state: dict, rid: str, status: str, aktivitas: str = "") -> None:
    p = state["pekerja"].setdefault(rid, {})
    p["status"] = status
    if aktivitas:
        p["aktivitas"] = aktivitas
    if status == "working":
        p["mulai"] = time.time()
    elif status in ("done", "idle") and p.get("mulai"):
        p["durasi_s"] = round(time.time() - p["mulai"], 1)
    state["tahap"] = rid
    write_status(state)


# ---------------------------------------------------------------- tahapan

SYS_BASE = (
    "Kamu pekerja di kantor berita keuangan Indonesia yang profesional dan teliti. "
    "Selalu jawab dalam Bahasa Indonesia jurnalistik yang jelas. "
    "Pakai HANYA fakta dan angka yang ada di bahan sumber. Jangan mengarang angka, "
    "kutipan, atau peristiwa. Kalau sebuah data tidak ada di bahan sumber, tulis apa "
    "adanya bahwa data itu belum tersedia. Jangan menyebut nama institusi atau lembaga "
    "tempat bekerja; tulis berita secara generik."
)


def _bahan_sumber(headlines: list[dict], isi: dict[str, str], maks: int = 6) -> str:
    """Rangkai bahan sumber: judul + isi artikel, untuk grounding model."""
    bagian = []
    for i, h in enumerate(headlines[:maks]):
        teks = isi.get(h["tautan"], "")
        kepala = (f"[S{i+1}] {h['judul']} \u2014 {h['sumber']} "
                  f"({h.get('wilayah', 'indonesia')}, {h['waktu'][:25]})\n"
                  f"{teks or h['ringkas']}")
        bagian.append(kepala)
    return "\n\n".join(bagian)


def stage_riset(state: dict, headlines: list[dict], topik_paksa: str | None,
                arsip: list[dict]) -> str:
    rid = "riset"
    set_status(state, rid, "working", "menyisir feed berita")

    # tarik isi artikel untuk 8 headline teratas supaya ada bahan nyata
    from concurrent.futures import ThreadPoolExecutor
    isi: dict[str, str] = {}
    kandidat = [h for h in headlines[:8] if h["tautan"]]
    with ThreadPoolExecutor(max_workers=8) as ex:
        for h, t in zip(kandidat, ex.map(lambda x: tarik_isi_artikel(x["tautan"]), kandidat)):
            if t:
                isi[h["tautan"]] = t
    log(f"isi artikel ditarik: {len(isi)}/{len(kandidat)}")
    state["_isi"] = isi

    riwayat = ""
    if arsip:
        riwayat = ("\n\nTOPIK YANG SUDAH PERNAH TERBIT (JANGAN pilih topik yang mirip "
                   "atau mengulang ini):\n" +
                   "\n".join(f"- {a['topik']}" for a in arsip[-15:]))

    if topik_paksa:
        state["topik"] = topik_paksa
        bahan = _bahan_sumber(headlines, isi)
        out = (f"TOPIK TERPILIH: {topik_paksa}\n\n"
               f"BAHAN SUMBER (judul + isi artikel):\n{bahan}\n\n"
               f"FAKTA AWAL: Topik ini dipilih langsung oleh editor manusia. "
               f"Reporter mencatat fakta pendukung dari bahan sumber di atas.")
    else:
        daftar = "\n".join(
            f"{i+1}. {h['judul']} | {h['sumber']} | {h['waktu'][:25]}\n   {h['ringkas'][:200]}"
            for i, h in enumerate(headlines))
        bahan = _bahan_sumber(headlines, isi, maks=5)
        user = (f"Headline terbaru dari beberapa kanal berita keuangan:\n\n{daftar}\n\n"
                f"ISI ARTIKEL TERPILIH (bahan sumber):\n{bahan}{riwayat}\n\n"
                "Pilih SATU topik paling layak diberitakan hari ini, yang belum pernah "
                "terbit sebelumnya. Lalu keluarkan:\n"
                "TOPIK TERPILIH: <judul topik>\n"
                "ALASAN: <kenapa penting>\n"
                "FAKTA AWAL:\n- <fakta 1>\n- <fakta 2>\n- <fakta 3>\n"
                "SUMBER: <nama sumber dan judul aslinya>")
        out = call_model(role_model(rid), SYS_BASE, user, CFG["max_tokens"]["riset"])
        m = re.search(r"TOPIK TERPILIH\s*:\s*(.+)", out)
        if m:
            topik = m.group(1).strip().splitlines()[0][:160]
            if _topik_pernah_dibahas(topik, arsip):
                log(f"topik mirip arsip, tetap dipakai: {topik}")
            state["topik"] = topik

    set_status(state, rid, "done", f"topik: {state.get('topik', '')[:60]}")
    return out


def _headline_relevan(state: dict, headlines: list[dict], maks: int = 4,
                      ambang: float = 0.12) -> list[dict]:
    """Headline yang relevan dengan topik terpilih (di atas ambang kemiripan)."""
    topik = state.get("topik", "")
    isi: dict[str, str] = state.get("_isi", {})
    skor = [(h, mirip(topik, h["judul"])) for h in headlines]
    skor.sort(key=lambda x: -x[1])
    pilih = [h for h, s in skor if s >= ambang and isi.get(h["tautan"])][:maks]
    return pilih or [h for h, _ in skor[:1]] or headlines[:1]


def _bahan_relevan(state: dict, headlines: list[dict], maks: int = 4) -> str:
    """Isi artikel yang paling relevan dengan topik terpilih."""
    pilih = _headline_relevan(state, headlines, maks)
    return _bahan_sumber(pilih, state.get("_isi", {}), maks=maks)


def _sumber_relevan(state: dict, headlines: list[dict], maks: int = 4) -> list[dict]:
    """Daftar sumber yang benar-benar dipakai untuk topik terpilih."""
    return _headline_relevan(state, headlines, maks)


def stage(rid: str, state: dict, user: str, sistem_tambahan: str = "") -> str:
    role = BY_ID[rid]
    set_status(state, rid, "working", role["tugas"].lower())
    sistem = SYS_BASE
    if sistem_tambahan:
        sistem += " " + sistem_tambahan
    out = call_model(role_model(rid), sistem, user, CFG["max_tokens"][rid])
    set_status(state, rid, "done", role["tugas"])
    return out


def role_model(rid: str) -> str:
    return BY_ID[rid]["model"]


def _ambil(teks: str, label: str) -> str:
    """Ambil isi setelah 'LABEL:' sampai label besar berikutnya."""
    m = re.search(rf"(?im)^\s*\**\s*{re.escape(label)}\s*\**\s*:\s*(.+)$", teks)
    if not m:
        return ""
    return m.group(1).strip()


def _badan_artikel(naskah: str) -> str:
    """Buang baris judul di awal naskah editor, sisakan badan berita."""
    lines = [ln.rstrip() for ln in naskah.strip().splitlines()]
    while lines and (not lines[0].strip() or lines[0].lstrip().startswith("#")
                     or lines[0].lstrip().startswith("**JUDUL")):
        if lines[0].lstrip().startswith("#") or lines[0].lstrip().startswith("**JUDUL"):
            lines.pop(0)
            break
        lines.pop(0)
    body = "\n".join(lines).strip()
    return body


def produce(topik_paksa: str | None = None) -> dict:
    run_id = datetime.now(WIB).strftime("%Y%m%d-%H%M%S")
    state = {"run_id": run_id, "pekerja": {}, "selesai": False, "topik": topik_paksa}
    write_status(state)
    log(f"=== mulai produksi {run_id} ===")

    arsip = muat_arsip()
    headlines = fetch_headlines(CFG["jumlah_headline"])
    log(f"headline terkumpul: {len(headlines)}")
    if not headlines:
        log("PERINGATAN: tidak ada headline, pakai topik paksa")

    hasil: dict[str, str] = {}

    hasil["riset"] = stage_riset(state, headlines, topik_paksa, arsip)
    log(f"riset selesai, topik: {state.get('topik')}")

    bahan = _bahan_relevan(state, headlines)
    state["_sumber"] = _sumber_relevan(state, headlines)
    log(f"bahan relevan disiapkan: {len(bahan)} karakter")

    hasil["analis"] = stage("analis", state,
        f"TOPIK: {state.get('topik')}\n\nHASIL RISET REPORTER:\n{hasil['riset']}\n\n"
        f"BAHAN SUMBER (isi artikel, pakai angkanya):\n{bahan}\n\n"
        "Beri analisis: penyebab, pihak terdampak, 2-3 angka kunci yang ADA di bahan "
        "sumber, dan satu sudut pandang yang membedakan dari media lain. "
        "Kalau angka tidak ada di bahan, sebut belum tersedia.")
    log("analis selesai")

    hasil["penulis"] = stage("penulis", state,
        f"TOPIK: {state.get('topik')}\n\nRISET:\n{hasil['riset']}\n\n"
        f"ANALISIS:\n{hasil['analis']}\n\nBAHAN SUMBER (isi artikel, pakai angkanya):\n{bahan}\n\n"
        "Tulis draft berita lengkap dengan format PERSIS seperti ini:\n"
        "JUDUL: <judul>\nLEAD: <1 paragraf pembuka kuat>\n"
        "ISI: <5-6 paragraf, tiap paragraf dipisah baris kosong>\nPENUTUP: <1 paragraf>\n"
        "Sertakan angka yang ADA di bahan sumber. Jangan mengarang kutipan atau angka.")
    log("penulis selesai")

    hasil["editor"] = stage("editor", state,
        f"DRAFT DARI PENULIS:\n{hasil['penulis']}\n\n"
        "Sunting jadi naskah jurnalistik siap tayang. Pertahankan fakta dan angka, "
        "jangan tambah data baru. Keluarkan naskah lengkap hasil suntingan, "
        "diawali satu baris judul, lalu lead, lalu isi.")
    log("editor selesai")

    hasil["verifikator"] = stage("verifikator", state,
        f"NASKAH:\n{hasil['editor']}\n\nBAHAN SUMBER (rujukan):\n{bahan}\n\n"
        "Periksa tiap klaim angka dan pernyataan: cocokkan ke bahan sumber. Keluarkan:\n"
        "KLAIM DIPERIKSA:\n- <klaim> -> <status: kuat/perlu data/berisiko>\n"
        "CATATAN KEHATI-HATIAN:\n- <catatan untuk penerbit>",
        sistem_tambahan="Kamu teliti dan skeptis; tandai klaim yang tidak ada di bahan sumber.")
    log("verifikator selesai")

    hasil["penerbit"] = stage("penerbit", state,
        f"NASKAH FINAL:\n{hasil['editor']}\n\nCATATAN VERIFIKATOR:\n{hasil['verifikator']}\n\n"
        "Keluarkan dengan format PERSIS seperti ini:\n"
        "JUDUL FINAL: <judul>\nRINGKASAN: <2 kalimat>\n"
        "TAGAR: <5 tagar dipisah spasi>\nDISCLAIMER: <satu kalimat etika/kehati-hatian>")
    log("penerbit selesai")

    state["selesai"] = True
    state["tahap"] = "selesai"
    write_status(state)

    judul_final = _ambil(hasil["penerbit"], "JUDUL FINAL") or state.get("topik", "")
    ringkasan = _ambil(hasil["penerbit"], "RINGKASAN")
    tagar = _ambil(hasil["penerbit"], "TAGAR")
    disclaimer = _ambil(hasil["penerbit"], "DISCLAIMER")
    badan = _badan_artikel(hasil["editor"])

    sumber_md = "\n".join(
        f"- {h['judul']} \u2014 {h['sumber']} [{h.get('wilayah', 'indonesia')}]"
        + (f" ({h['tautan']})" if h["tautan"] else "")
        for h in state.get("_sumber", headlines[:4]))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    waktu = datetime.now(WIB).strftime("%Y-%m-%d %H:%M WIB")

    # 1) artikel bersih siap baca
    (OUT_DIR / f"berita-{run_id}.md").write_text(
        f"# {judul_final}\n\n"
        + (f"_{ringkasan}_\n\n" if ringkasan else "")
        + f"{badan}\n\n"
        + (f"**Tagar:** {tagar}\n\n" if tagar else "")
        + (f"_{disclaimer}_\n\n" if disclaimer else "")
        + "---\n\n"
        + f"*Kantor Berita Finance \u00b7 {waktu} \u00b7 edisi {run_id}*\n\n"
        + f"**Sumber:**\n{sumber_md}\n",
        encoding="utf-8")

    # 2) catatan proses redaksi (audit, terpisah dari artikel)
    (OUT_DIR / f"catatan-{run_id}.md").write_text(
        f"# Catatan Proses Redaksi \u2014 edisi {run_id}\n\n"
        f"- Waktu: {waktu}\n- Topik: {state.get('topik')}\n"
        f"- Jumlah headline: {len(headlines)}\n\n"
        + "\n\n".join(
            f"## {BY_ID[k]['jabatan']} ({BY_ID[k]['nama']})\n\n{v}"
            for k, v in hasil.items())
        + "\n",
        encoding="utf-8")

    # 3) data mentah lengkap
    (OUT_DIR / f"berita-{run_id}.json").write_text(
        json.dumps({
            "run_id": run_id, "waktu": waktu, "topik": state.get("topik"),
            "judul_final": judul_final, "ringkasan": ringkasan, "tagar": tagar,
            "disclaimer": disclaimer, "hasil": hasil, "headline": headlines,
        }, ensure_ascii=False, indent=2), encoding="utf-8")

    simpan_arsip(state.get("topik", ""), judul_final)
    log(f"=== selesai: output/berita-{run_id}.md (+ catatan + json) ===")

    time.sleep(1)
    for role in ROLES:
        p = state["pekerja"].get(role["id"])
        if p and p.get("status") == "done":
            p["status"] = "idle"
    write_status(state)
    return {"run_id": run_id, "topik": state.get("topik"), "judul": judul_final,
            "hasil": hasil}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--topik", default=None, help="paksa topik tertentu")
    a = ap.parse_args()
    try:
        r = produce(a.topik)
        print("\nSELESAI. run_id =", r["run_id"])
        print("JUDUL:", r["judul"])
    except KeyboardInterrupt:
        print("\ndihentikan")
