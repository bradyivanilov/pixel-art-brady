# Pixel Art Brady

Dua project Python yang saling melengkapi: satu kantor berita otomatis, satu
ruang kantor virtual berbasis kanvas.

## Isi repo

`kantor-finance` — mesin redaksi otomatis. Menarik berita dari 25 feed lintas
wilayah, mengolahnya lewat enam tahap (riset, analis, penulis, editor,
verifikator, penerbit), lalu mengeluarkan artikel bersih, catatan audit, dan data
mentah. Ada juga `kartu.py` yang mengubah hasil produksi jadi kartu gambar
1080x1080 plus caption untuk TikTok dan Instagram.

`hermes-pixel-office` — ruang kantor virtual. Server Python standar yang
menyajikan dua halaman: papan pantau Hermes dan kantor isometrik berisi karakter
yang digambar dari data hidup.

## Cara menjalankan

Kantor finance:

```
cd kantor-finance
python engine.py                 # produksi otomatis dari feed
python engine.py --topik "..."   # produksi dengan topik pilihan
python kartu.py                  # bikin kartu gambar + caption
```

Pixel office:

```
cd hermes-pixel-office
python server.py
```

Lalu buka `http://localhost:8770/` untuk papan pantau dan
`http://localhost:8770/kantor` untuk kantor isometrik.

## Kebutuhan

Python 3.10 atau lebih baru. Kantor finance membaca kunci API model dari
variabel lingkungan, jadi siapkan kunci sendiri di `.env`. Pixel office hanya
butuh pustaka standar Python.

## Catatan

Folder `output`, `kartu-kartu`, `kantor.log`, `status.json`, dan `arsip.json`
sengaja tidak ikut di repo. Itu hasil produksi dan data runtime, bukan bagian
dari kode.
