"""Pekerja di Kantor Berita Finance.

Tiap entri = satu karakter di pixel office + satu job desc nyata.
Ruangan: newsroom (riset & analis), writers (penulis & editor),
         factcheck (verifikator), publishing (penerbit).
"""

ROLES = [
    {
        "id": "riset",
        "nama": "Rani",
        "jabatan": "Reporter Riset",
        "room": "newsroom",
        "meja": 0,
        "model": "ag/gemini-3.8-flash",
        "warna": {"kulit": "#f2c9a0", "rambut": "#2b2118", "baju": "#e0533d", "celana": "#2f3550"},
        "jobdesc": (
            "Menyisir feed berita keuangan, memilih satu topik paling layak "
            "diberitakan hari ini, lalu mengumpulkan fakta mentahnya: judul, sumber, "
            "angka penting, dan waktu kejadian."
        ),
        "tugas": "Pilih topik & kumpulkan fakta",
    },
    {
        "id": "analis",
        "nama": "Dimas",
        "jabatan": "Analis Pasar",
        "room": "newsroom",
        "meja": 1,
        "model": "ag/claude-sonnet-4-6",
        "warna": {"kulit": "#e8b98d", "rambut": "#171310", "baju": "#3d7ce0", "celana": "#2f3550"},
        "jobdesc": (
            "Membedah topik dari reporter: apa penyebabnya, siapa yang terdampak, "
            "angka mana yang paling penting, dan sudut pandang apa yang belum "
            "diangkat media lain."
        ),
        "tugas": "Beri konteks & sudut pandang",
    },
    {
        "id": "penulis",
        "nama": "Sari",
        "jabatan": "Penulis Berita",
        "room": "writers",
        "meja": 0,
        "model": "homres",
        "warna": {"kulit": "#f2c9a0", "rambut": "#4a2c18", "baju": "#d94f9c", "celana": "#2f3550"},
        "jobdesc": (
            "Menulis draft berita lengkap: judul, lead tajam, isi lima sampai enam "
            "paragraf, angka pendukung, dan penutup yang mengikat."
        ),
        "tugas": "Tulis draft berita",
    },
    {
        "id": "editor",
        "nama": "Bagas",
        "jabatan": "Editor Meja",
        "room": "writers",
        "meja": 1,
        "model": "ag/claude-sonnet-4-6",
        "warna": {"kulit": "#e8b98d", "rambut": "#1c1c1c", "baju": "#8a5cd6", "celana": "#2f3550"},
        "jobdesc": (
            "Menyunting draft: rapikan struktur dan alur, ganti gaya bahasa jadi "
            "jurnalistik, buang klise, pastikan judul dan lead sinkron dengan isi."
        ),
        "tugas": "Sunting & rapikan",
    },
    {
        "id": "verifikator",
        "nama": "Nadia",
        "jabatan": "Verifikator Fakta",
        "room": "factcheck",
        "meja": 0,
        "model": "gh/gpt-4o-mini",
        "warna": {"kulit": "#f2c9a0", "rambut": "#3a2418", "baju": "#2fa36b", "celana": "#2f3550"},
        "jobdesc": (
            "Memeriksa tiap klaim angka dan pernyataan di naskah, menandai yang "
            "belum kuat dasarnya, dan menulis catatan kehati-hatian untuk penerbit."
        ),
        "tugas": "Verifikasi klaim",
    },
    {
        "id": "penerbit",
        "nama": "Yoga",
        "jabatan": "Editor Publikasi",
        "room": "publishing",
        "meja": 0,
        "model": "ag/gemini-3.8-flash",
        "warna": {"kulit": "#e8b98d", "rambut": "#241a10", "baju": "#e0a33d", "celana": "#2f3550"},
        "jobdesc": (
            "Menetapkan judul final, ringkasan, tagar, dan catatan etika atau "
            "disclaimer sebelum berita dinyatakan siap tayang."
        ),
        "tugas": "Finalkan & siapkan tayang",
    },
]

BY_ID = {r["id"]: r for r in ROLES}
