# Serah-terima UI/UX untuk OpenCode

Dokumen ini buat siapa pun (termasuk OpenCode) yang mau baca ulang atau nulis ulang
tampilan pixel office. Semua yang perlu tahu ada di sini.

## Peta berkas

Semua ada di `E:\Projects\hermes-pixel-office\`.

`index.html` 360 baris. Tampilan Kantor Hermes. Sesi Hermes kamu jadi karakter.
`kantor.html` 511 baris. Tampilan Kantor Berita Finance. Enam pekerja AI, ruangan isometrik.
`server.py` 201 baris. Server Python murni, tanpa dependensi luar.

Nggak ada folder asset. Nggak ada framework. Nggak ada build step. Nggak ada npm.
Semua CSS ada di dalam tag style, semua gambar digambar pakai canvas 2D di dalam tag script.
Buka filenya, langsung jalan.

## Gaya visual kantor.html (perhatikan, ini baru)

kantor.html sekarang bergaya isometrik hangat ala pixel art, bukan lagi denah kotak datar.
Ciri-cirinya: lantai kotak-kotak coklat, dinding biru gelap, jendela kuning dengan pemandangan
malam, rak buku di dinding, tanaman pot, monitor CRT di tiap meja, lampu gantung, papan tulis
berisi sticky note, dan tiap pekerja punya gelembung bicara di atas kepalanya berisi tugasnya.
Kartu pekerja di bawah canvas menampilkan jabatan, status, job desc, dan daftar tugas.

Kalau kamu mau meniru gaya ini, kuncinya: gambar pakai urutan dari belakang ke depan
(dinding dulu, lalu lantai, lalu furnitur, lalu karakter, terakhir gelembung bicara),
supaya tumpukan gambarnya benar. Semua bentuk dibuat dari fungsi kotak `px`.

## Di baris berapa apa (kantor.html)

Baris 1 sampai 46, tag head plus seluruh CSS di dalam style. Variabel warna ada di
`:root`, misalnya `--bg` latar, `--panel` kotak, `--line` garis, `--ink` teks terang,
`--dim` teks redup. Ganti tema cukup di sini.

Baris 64, elemen canvas `<canvas id="c" width="2240" height="1440">`. Atribut width dan
height menentukan resolusi internal.

Baris 75 mulai blok script. Isinya berurutan seperti ini.

Pertama, baris 75 sampai 80, ambil canvas dan context, lalu set `SCALE = 2` dan
`ctx.setTransform(SCALE,...)`. Dunia gambar efektif jadi 1120 kali 720 (`W` dan `H`).
Semua posisi ditulis dalam koordinat kecil itu, jadi jangan bingung kalau angkanya terlihat setengah.

Kedua, `drawFloor` di baris 125 dan `drawWalls` di baris 145. Ini yang menggambar lantai
kotak-kotak dan dinding plus jendela.

Ketiga, `drawScene` di baris 316. Ini yang menata seluruh ruangan: rak buku, meja, monitor,
tanaman, papan tulis, dan karakter. Urutan gambarnya dari belakang ke depan.

Keempat, `draw` di baris 438, memanggil seluruh gambar panggung. Lalu `renderRoster` di
baris 459 yang mengisi kartu pekerja di bawah canvas. Lalu `poll` di baris 486 yang ambil
data dari server tiap lima detik dan panggil ulang gambar.

## Kontrak data dari server

Tampilan tidak menyimpan data sendiri. Semua diambil dari server di port 8770.

`GET /api/state` untuk halaman index. Bentuk balasannya: `ok` boolean, `count` jumlah
agent, `working` jumlah yang aktif, `db` lokasi database, `server_time`, dan `agents`
berisi daftar. Tiap agent punya id, name, source, model, status, tool, last_activity,
age_s, messages, tool_calls, tokens_in, tokens_out, cost_usd, ended.

`GET /api/kantor` untuk halaman kantor. Bentuk balasannya: `ok`, `sumber`, `diperbarui`,
`run_id`, `tahap`, `topik`, `selesai`, dan `pekerja` berisi daftar. Tiap pekerja punya
id, nama, jabatan, room, meja, warna, model, tugas, jobdesc, status, aktivitas, mulai,
durasi_s.

Contoh balasan nyata ada di `_api_sample.json` di folder yang sama.

Kalau kamu nulis ulang tampilannya, pertahankan dua endpoint ini apa adanya. Yang boleh
kamu ganti bebas itu cara menggambar, warna, tata letak, animasi. Yang jangan diganti
nama field dan alamat endpoint, karena server yang menyediakannya.

## Aturan yang wajib dijaga

Kanvas digambar di koordinat kecil lalu diperbesar `SCALE` kali. Jadi ukuran canvas
harus kelipatan `SCALE` dari ukuran panggung. Kalau panggung lebar 1120, canvas harus
2240. Salah hitung di sini bikin ruangan terpotong, persis bug yang dulu pernah kejadian
di kantor.html.

Jangan pasang `image-rendering: pixelated` di canvas kalau mau teks tajam. Itu yang dulu
bikin huruf jadi kotak-kotak.

Karakter digambar dari data, bukan ditempel gambar. Kalau mau ubah gaya karakter, ubah
fungsi gambarnya, bukan cari file sprite, karena memang nggak ada.

## Cara mengetes hasil kerja

Nyalakan server dulu, lalu buka alamatnya. Server jalan dengan perintah berikut.

`python server.py`

Halaman Hermes di `http://localhost:8770/`. Halaman kantor di `http://localhost:8770/kantor`.

Kalau mau lihat hasil tanpa buka browser, potret pakai Chrome headless. Catatan penting:
Chrome headless tidak bisa menulis ke drive E:, jadi arahkan screenshot ke folder temp.

`chrome --headless=new --disable-gpu --hide-scrollbars --virtual-time-budget=8000 --window-size=1400,1000 --screenshot="%TEMP%\_cek.png" "http://localhost:8770/kantor"`

Pakai `--virtual-time-budget=8000` supaya halaman selesai memuat dulu sebelum dipotret,
kalau tidak hasilnya bisa kejebak tulisan "memuat...". Lalu lihat gambarnya untuk memastikan
ruangan nggak terpotong dan label kebaca.
