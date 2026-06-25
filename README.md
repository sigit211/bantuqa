# BantuQa

BantuQa adalah aplikasi desktop Windows untuk membantu tim QA mengambil bukti layar, memberi anotasi, lalu mengirim hasil ke TestRail dari satu antarmuka.

**Status:** ✅ Repo saat ini memuat kode sumber, file build, dan script untuk menghasilkan executable Windows.

## Fitur yang tersedia di kode

- Login ke TestRail menggunakan URL, email, dan API key/password.
- Penyimpanan kredensial di Windows Credential Manager via `keyring`.
- Pemilihan project, plan, run, case, dan assignee dari API TestRail.
- Tampilan case berbasis langkah (`steps`) jika tersedia, atau tampilan teks.
- Capture screenshot lewat snipping tool yang bisa dipanggil dari dalam aplikasi maupun via hotkey global.
- Annotasi sederhana (`Pen`, `Box`, `Clear`) sebelum menyimpan gambar.
- Gallery / preview screenshot yang sudah ditangkap.
- Komentar per file dan komentar khusus per step.
- Upload attachment ke run TestRail.
- Submit hasil test ke case tertentu beserta komentar dan elapsed time.
- Timer dengan tombol `Start`, `Hold`, dan `Stop`.
- Tray icon dengan menu `Open Dashboard` dan `Exit`.
- Single instance agar hanya satu aplikasi berjalan.
- Global hotkey `Ctrl+Shift+S` untuk memulai capture dari luar aplikasi.

## Struktur proyek

### File inti
- `main.py` — entry point aplikasi; mengatur DPI awareness, logging, cek restart sistem, single instance, tray, dan hotkey.
- `src/ui.py` — UI utama menggunakan `customtkinter`.
- `src/api.py` — wrapper API TestRail untuk login, fetch data, upload attachment, dan submit result.
- `src/auth.py` — membaca / menyimpan kredensial ke credential manager.
- `src/capture.py` — snipping tool dan proses anotasi screenshot.
- `src/hotkey.py` — listener hotkey global.
- `src/tray.py` — tray icon dan menu.
- `src/single_instance.py` — mekanisme lock instance.

### File pendukung
- `requirements.txt` — dependency runtime aplikasi.
- `build.ps1` — script build executable dengan PyInstaller.
- `BantuQa.spec` — konfigurasi PyInstaller.
- `bantuqa_spec.md` — dokumentasi spesifikasi proyek.
- `patch_api.py` dan `fix.py` — utility tambahan untuk maintenance.
- `Screenshots/` — folder default untuk hasil capture.

## Prasyarat

- Windows
- Python 3.10+ (repo ini sudah memiliki folder `venv/` untuk lingkungan lokal)
- `pip`
- Opsional: PyInstaller untuk proses build

## Menjalankan dari source

1. Buka terminal di root project.
2. Aktifkan environment (opsional, tetapi disarankan):
   ```powershell
   .\venv\Scripts\Activate.ps1
   ```
3. Install dependency:
   ```powershell
   python -m pip install -r requirements.txt
   ```
4. Jalankan aplikasi:
   ```powershell
   python main.py
   ```

> Jika PowerShell memblokir aktivasi script, jalankan terlebih dahulu:
>
> ```powershell
> Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
> ```

## Build executable

Script build sudah tersedia dan akan menginstal PyInstaller jika diperlukan:

```powershell
.\build.ps1
```

Hasil build biasanya berada di:
- `dist\BantuQa.exe`
- `build/` sebagai output intermediate build

## Dependency yang dipakai

| Package | Kegunaan |
|---------|----------|
| `customtkinter` | UI utama |
| `Pillow` | pemrosesan gambar dan anotasi |
| `mss` | capture layar |
| `pynput` | hotkey global |
| `requests` | komunikasi API |
| `keyring` | penyimpanan kredensial aman |
| `pystray` | tray icon |
| `pyinstaller` | build executable (dipasang saat menjalankan script build) |

## Lokasi file yang dipakai

- Screenshot hasil capture disimpan di folder `Screenshots/` di root project, atau dalam subfolder per case ketika case tersedia.
- Log aplikasi ditulis ke `%TEMP%\BantuQa\BantuQa.log`.
- File sementara untuk proses capture berada di `%TEMP%\BantuQa`.

## Alur penggunaan

1. Saat pertama kali dijalankan, aplikasi menampilkan layar login.
2. Masukkan URL TestRail, email, dan API key/password.
3. Setelah login berhasil, pilih project, plan/run, lalu case yang akan dikerjakan.
4. Gunakan `Ctrl+Shift+S` atau tombol capture untuk mengambil screenshot.
5. Setelah screenshot muncul, lakukan anotasi jika diperlukan.
6. Review hasil di gallery dan tambahkan komentar bila perlu.
7. Klik `Upload Attachments` untuk mengunggah screenshot ke run yang dipilih.
8. Gunakan timer `Start` / `Hold` / `Stop`, lalu klik `Submit to TestRail`.

## Troubleshooting

### Hotkey tidak bekerja
- Pastikan `pynput` sudah terinstall dengan benar.
- Coba restart aplikasi.
- Jika aplikasi sedang berjalan di background, tekan `Ctrl+Shift+S` setelah aplikasi benar-benar aktif.

### Login gagal
- Periksa URL TestRail sudah benar.
- Gunakan email yang valid dan API key/password yang sesuai.
- Pastikan jaringan bisa mengakses TestRail.

### Upload gagal
- Pastikan run yang dipilih valid.
- Cek file screenshot tidak corrupt atau kosong.
- Lihat log di `%TEMP%\BantuQa\BantuQa.log`.

### Aplikasi tetap membuka lebih dari satu instance
- Tutup semua instance BantuQa terlebih dahulu.
- Jalankan ulang aplikasi dari source.

## Dokumentasi tambahan

- [bantuqa_spec.md](bantuqa_spec.md) — spesifikasi fungsi dan alur proyek

## Kontributor

- Developer: Sigit Wahyudi
- Email: s.wahyudi21@gmail.com

