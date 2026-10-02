# Hermes Pixel Office

Kantor piksel yang menampilkan sesi Hermes kamu sebagai karakter yang bergerak.
Ini bukan plugin Agent Pixels (itu buat Paperclip, sistem lain) — ini dibuat khusus
untuk Hermes, dan membaca state Hermes kamu langsung.

## Apa yang dilihat

Tiap karakter = satu sesi Hermes asli, dibaca langsung dari state.db (read-only).
Bukan animasi palsu: nama, model, jumlah pesan, token, dan tool terakhir semuanya data hidup.

Aturan geraknya:
- working  -> duduk di meja kerja, monitor nyala hijau
- active   -> nongkrong di lounge
- idle     -> muter di kantin, ruang rapat, dan ruang game

Warna baju tiap karakter stabil, jadi agent yang sama selalu kelihatan sama.

## Cara pakai

Klik dua kali JALANKAN.bat. Browser kebuka sendiri ke http://localhost:8770
Tutup jendela hitamnya kalau mau berhenti.

Atau manual:
    cd E:\Projects\hermes-pixel-office
    python server.py
lalu buka http://localhost:8770

## Dua halaman

1. `/` — **Pixel Office (Hermes)**: menampilkan sesi Hermes kamu sebagai karakter.
2. `/kantor` — **Kantor Berita Finance**: kantor virtual berisi 6 pekerja AI yang
   memproduksi berita keuangan berantai. Lihat `E:\Projects\kantor-finance\README.md`.

Pindah antar halaman lewat tab di atas kanvas.

## File

server.py     server kecil (stdlib Python, tanpa dependensi). Baca state.db read-only,
              sediakan /api/state (sesi Hermes) dan /api/kantor (pekerja kantor berita).
index.html    tampilan pixel office (canvas murni, tanpa library).
kantor.html   tampilan kantor berita finance.
JALANKAN.bat  launcher sekali klik.

## Nyambung ke mana

server.py cari state.db di urutan ini:
1. %HERMES_HOME%\state.db
2. %LOCALAPPDATA%\hermes\state.db   (lokasi normal di Windows)
3. ~\.hermes\state.db               (lokasi Linux/Mac)

Jadi kalau Hermes kamu pindah, tinggal set HERMES_HOME dan dia ikut.

## Aman

Cuma baca. Tidak pernah menulis, tidak pernah mengubah sesi, tidak menyentuh kredensial.
Server cuma bind ke 127.0.0.1, jadi cuma bisa diakses dari komputer ini.

## Mau diubah

Ganti port:  set PIXEL_OFFICE_PORT=9000  sebelum jalanin.
Tambah ruangan: ubah objek ROOMS di index.html.
Tambah karakter: tambah entri di array PALETTES.
Kartu kanan: edit fungsi renderRoster().
