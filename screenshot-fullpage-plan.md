# Rencana Fitur Screenshot Full-Web

## Tujuan
Menambahkan tombol screenshot baru di panel `Attachment & Actions` yang dapat menangkap halaman web penuh (full page) dari browser yang sudah aktif, terutama Chrome, Firefox, dan Microsoft Edge.

## Scope
- Tambah tombol baru di panel `Attachment & Actions`.
- Buat floating popup yang muncul ketika tombol di klik.
- Popup berfungsi sebagai trigger: sistem hanya mengambil screenshot setelah user menekan tombol `Start Screenshot` di popup.
- Popup harus tetap berada di atas browser agar user bisa menyiapkan halaman web dan memilih browser yang sudah aktif.
- Implementasi harus mendukung mengambil screenshot dari browser yang sudah dibuka, bukan membuka browser baru.
- Implementasi annotation window harus mendukung scrollbar untuk screenshot tinggi.
- Batasi dukungan browser ke Chrome, Firefox, dan Edge.

## Langkah Implementasi

1. UI
   - `src/ui.py`
   - Tambahkan tombol baru di samping tombol `➕` di sub-panel `Attachment & Actions`.
   - Tombol baru memanggil handler `request_fullpage_capture`.
   - Pastikan tombol hanya aktif setelah sesi testing berjalan.

2. Popup Floating
   - Buat `Toplevel` atau `CTkToplevel` floating dengan `-topmost=True`.
   - Popup berisi instruksi singkat, input URL atau judul/tab browser, dan tombol `Start Screenshot`.
   - Jangan langsung capture ketika popup muncul; tunggu sampai user klik tombol.
   - Popup harus memungkinkan user menyiapkan halaman browser terlebih dahulu.

3. Capture dari Browser Aktif
   - Gunakan pendekatan attach ke browser yang sudah berjalan dengan:
     - Chrome/Edge melalui remote debugging port, atau
     - Firefox melalui remote debugging/profil khusus.
   - Alternatif lain: gunakan extension browser untuk mengambil screenshot dari tab aktif.
   - Jika browser aktif tidak dapat ditemukan atau tidak mendukung attach, beri instruksi agar user membuka browser dengan opsi remote debugging atau gunakan browser yang sesuai.
   - Tetapkan prioritas dukungan:
     - Chrome / Edge (Chromium)
     - Firefox

4. Logika dan Fallback
   - Jika tidak bisa attach langsung ke browser yang sudah aktif, tampilkan pesan jelas.
   - Jika browser sudah terbuka tapi tidak bisa diattach, opsi fallback bisa berupa membuka browser baru hanya setelah user setuju.
   - Pastikan flow tidak otomatis membuka browser baru tanpa konfirmasi.

5. Anotasi
   - `src/capture.py`
   - Perbaiki `AnnotationWindow` agar mendukung scrollbar ketika menampilkan gambar tinggi.
   - Pastikan UI anotasi dapat menampilkan seluruh screenshot full-page, atau setidaknya memungkinkan scrolling vertikal.

6. Packaging dan Installer
   - `requirements.txt` harus ditambahkan dependensi baru jika diperlukan (misalnya `selenium`, `playwright`, atau library remote debugging).
   - `build.ps1` perlu diperbarui untuk packaging.
   - Buat installer yang menyertakan `.exe` utama dan komponen tambahan jika perlu.
   - Installer harus memastikan dukungan untuk Chrome, Firefox, dan Edge, termasuk instruksi konfigurasi remote debugging jika dibutuhkan.

## File Terkait
- `src/ui.py`
- `src/capture.py`
- `main.py`
- `requirements.txt`
- `build.ps1`

## Verifikasi
1. Tombol baru muncul di sebelah `➕` dan dapat diklik saat sesi berjalan.
2. Popup floating tampil di atas browser.
3. Screenshot hanya diambil setelah user klik tombol `Start Screenshot`.
4. Sistem mencoba attach ke browser yang sudah aktif, bukan langsung membuka browser baru.
5. Jika attach tidak berhasil, tampilkan instruksi fallback yang jelas.
6. Annotation window mendukung scrollbar untuk tampilan gambar tinggi.

## Catatan
- Fitur ini harus fokus pada browser yang sudah terbuka, bukan membuka browser baru.
- Untuk Chrome/Edge, attach via remote debugging adalah pendekatan yang paling realistis.
- Untuk Firefox, perlu konfigurasi remote debugging atau profil khusus.
- Installer atau dokumentasi harus menjelaskan konfigurasi browser tambahan bila diperlukan agar attach bisa berjalan.
