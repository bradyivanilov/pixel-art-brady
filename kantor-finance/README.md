# Kantor Berita Finance — Virtual Office

Kantor berita yang dikerjakan oleh agent AI. Tiap pekerja punya job desc sendiri dan
saling menyambung: hasil satu pekerja dioper ke pekerja berikutnya, seperti ruang
redaksi sungguhan. Tampilannya menyatu dengan **Hermes Pixel Office** (halaman
`/kantor`), jadi kamu bisa lihat siapa sedang kerja, real-time.

## Alur kerja

    Rani (Riset)  →  Dimas (Analis)  →  Sari (Penulis)  →  Bagas (Editor)
                  →  Nadia (Verifikator)  →  Yoga (Penerbit)  →  output/

Setiap kotak adalah **satu panggilan model nyata** ke 9router. Bukan animasi.

| Pekerja | Jabatan | Ruangan | Model | Job desc |
|---|---|---|---|---|
| Rani | Reporter Riset | NEWSROOM | gemini-3.8-flash | Pilih topik, kumpulkan fakta dari feed |
| Dimas | Analis Pasar | NEWSROOM | claude-sonnet-4-6 | Konteks, pihak terdampak, sudut pandang |
| Sari | Penulis Berita | WRITERS | homres | Tulis draft berita lengkap |
| Bagas | Editor Meja | WRITERS | claude-sonnet-4-6 | Sunting struktur & gaya jurnalistik |
| Nadia | Verifikator Fakta | FACT CHECK | gpt-4o-mini | Periksa klaim, tandai yang berisiko |
| Yoga | Editor Publikasi | PUBLISHING | gemini-3.8-flash | Judul final, tagar, disclaimer |

## Cara pakai

1. Klik dua kali **PRODUKSI.bat**. Server pixel office nyala sendiri, browser kebuka.
2. Pilih `1` kalau mau topik dipilih otomatis dari feed berita.
   Pilih `2` kalau mau tentukan topik sendiri.
3. Lihat di browser: karakter yang sedang kerja punya label kuning.
4. Hasilnya ada di folder `output/` (lihat bagian Format keluaran).

Bisa juga dari terminal:

    python engine.py                                   # topik otomatis
    python engine.py --topik "Harga emas naik"         # topik sendiri

## Format keluaran

Tiap produksi menghasilkan TIGA berkas, supaya artikel bersih tidak tercampur
catatan proses:

    berita-<id>.md    artikel bersih siap dibaca: judul, ringkasan, isi, tagar,
                      disclaimer, dan daftar sumber. Tidak ada instruksi internal.
    catatan-<id>.md   catatan proses redaksi untuk audit: riset, analisis,
                      verifikasi klaim. Terpisah dari artikel.
    berita-<id>.json  data mentah lengkap semua tahap + headline + sumber.

Berkas edisi lama yang masih berformat gabungan dipindah ke `output/lama/`.

## Sumber berita (input)

Feed diatur di `config.json`. Ada 25 feed, dibagi per wilayah, semuanya sudah
diverifikasi hidup dan isi artikelnya bisa ditarik:

- Indonesia (10): CNBC Market, CNBC News, CNBC Syariah, Detik Finance,
  Antara Ekonomi, Katadata, IDX Channel, Liputan6 Bisnis, Republika Ekonomi,
  Warta Ekonomi.
- Global (3): BBC Business, Al Jazeera, SCMP Business.
- ASEAN (3): CNA, Straits Times Business, VnExpress Business.
- Eropa (3): Euronews Business, The Guardian Business, DW Business.
- Amerika (3): NYT Business, Yahoo Finance, CNBC US Business.
- Arab (3): Asharq Al-Awsat, AGBI, Middle East Monitor.

Semua feed ditarik paralel, jadi total ambil berita cuma sekitar 3 detik walau
feednya banyak. Kalau satu feed mati, produksi tetap jalan dengan feed lain.

Hasilnya juga diseimbangkan: tiap wilayah kebagian jatah sama, jadi berita tidak
didominasi Indonesia saja. Untuk feed berita umum (CNA, Al Jazeera, dan sejenisnya)
judulnya disaring dulu pakai kata kunci bisnis, supaya yang masuk cuma berita
ekonomi, bukan olahraga atau kriminal.

Yang penting: reporter tidak cuma baca judul. Untuk tiap headline teratas,
isi artikelnya ikut ditarik dan dijadikan bahan sumber. Isi itu yang dioper
ke analis, penulis, dan verifikator, jadi angka dan kutipan di berita benar-benar
ada dasarnya. Data yang tidak ada di bahan sumber ditulis apa adanya sebagai
belum tersedia, bukan dikarang.

Kantor juga punya memori: topik yang sudah pernah terbit dicatat di `arsip.json`
dan tidak dipilih lagi pada produksi berikutnya.

## Menambah pekerja baru

Buka `roles.py`, tambah satu blok di daftar `ROLES`. Contoh menambah "Fotografer":

    {
        "id": "foto",
        "nama": "Bimo",
        "jabatan": "Fotografer",
        "room": "writers",          # newsroom / writers / factcheck / publishing
        "meja": 2,                  # 0-3, menentukan posisi di ruangan
        "model": "ag/gemini-3.8-flash",
        "warna": {"kulit":"#e8b98d","rambut":"#241a10","baju":"#40a0d0","celana":"#2f3550"},
        "jobdesc": "Menyiapkan gambar pendukung berita.",
        "tugas": "Siapkan gambar",
    },

Lalu panggil dia di `engine.py` pada `produce()`, mengikuti pola `stage("foto", state, ...)`.
Ruangan baru bisa ditambah di `ROOMS` pada file `kantor.html`.

## Berkas

    roles.py       daftar pekerja + job desc + warna + model
    config.json    feed berita, jumlah headline, batas token per tahap
    engine.py      mesin produksi (alur berantai)
    status.json    status live tiap pekerja (dibaca halaman /kantor)
    arsip.json     memori topik yang sudah pernah terbit
    kantor.log     catatan tiap langkah
    output/        hasil berita: berita-<id>.md, catatan-<id>.md, berita-<id>.json

## Catatan

Pekerja diberi aturan supaya tidak mengarang angka atau kutipan. Kalau data tidak
tersedia, mereka menulisnya apa adanya sebagai belum tersedia — seperti yang kamu lihat
di contoh output: reporter menandai data rupiah kosong, penulis menulisnya jujur, dan
verifikator menandai klaim lemah sebagai berisiko.
