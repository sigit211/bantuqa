# Business Logic BantuQa

Dokumen ini menjelaskan aturan bisnis utama aplikasi BantuQa agar alur penggunaan sesuai dengan kebutuhan QA/TestRail.

## 1. Tujuan Utama
- Memudahkan pengguna mengambil screenshot bukti selama proses testing.
- Menghitung durasi pengerjaan test secara akurat.
- Mengunggah screenshot ke TestRail hanya setelah data siap.

## 2. Aturan Bisnis Utama

| No | Aturan | Kondisi | Hasil |
|---|---|---|---|
| 1 | Wajib login sebelum menggunakan fitur utama | Pengguna belum login | Aplikasi menampilkan layar login |
| 2 | Tidak bisa mengambil screenshot sebelum memulai sesi testing | Tombol play (`▶`) belum diklik | Screenshot tidak boleh diproses; sistem menampilkan peringatan |
| 3 | Tombol screenshot hanya aktif saat sesi berjalan | Timer sedang berjalan (not paused) | Pengguna boleh mengambil screenshot |
| 4 | Status result harus dipilih sebelum submit | Status result masih kosong, belum berubah dari `Untested`, atau belum sesuai dengan hasil pengujian | Sistem mencegah submit sampai status valid dipilih |
| 5 | Status result dapat diubah selama sesi berjalan | Timer sudah mulai dan pengujian masih berlangsung | Pengguna dapat memperbarui status kapan saja sebelum submit |
| 6 | Komentar hasil test hanya boleh diisi saat sesi berjalan | Timer belum berjalan atau sedang pause | Input komentar dinonaktifkan |
| 7 | Upload attachment harus dilakukan sebelum submit | Terdapat screenshot yang belum diupload | Tombol submit dinonaktifkan |
| 8 | Submit hanya boleh dilakukan jika ada durasi kerja yang valid | Waktu kerja masih 0 detik | Tombol submit tetap nonaktif |
| 9 | Screenshot yang sudah diambil harus tersimpan dalam queue | Screenshot berhasil ditangkap | Screenshot muncul di daftar attachment |
| 10 | Screenshot dapat dihapus dari queue sebelum upload | File masih ada di queue | File dihapus dari daftar dan tidak ikut upload |
| 11 | Timer dapat dijeda dan dilanjutkan | Tombol pause/resume digunakan | Durasi kerja tetap tersimpan |
| 12 | Hasil submit harus mengandung evidence yang lengkap | Semua attachment sudah terupload | Data hasil test dapat dikirim ke TestRail |

## 3. Alur Bisnis yang Disarankan

### 3.1 Login
1. Pengguna memasukkan URL TestRail, username, dan password/API key.
2. Sistem memvalidasi kredensial.
3. Jika valid, pengguna masuk ke dashboard.

### 3.2 Memulai Testing
1. Pengguna memilih Project/Test Plan/Test Run.
2. Pengguna memilih test case.
3. Pengguna menekan tombol play (`▶`) untuk memulai timer.
4. Setelah timer berjalan, pengguna dapat memilih status result yang sesuai (misalnya Passed, Failed, Blocked, dll.).
5. Status default `Untested` tidak boleh dianggap final dan harus diperbarui sebelum submit.
6. Setelah timer berjalan, fitur screenshot dan komentar menjadi aktif.

### 3.3 Capture Screenshot
1. Pengguna menekan tombol capture atau menggunakan hotkey.
2. Sistem hanya memperbolehkan capture jika timer sedang berjalan.
3. Hasil capture disimpan ke folder screenshot dan masuk ke queue.

### 3.4 Upload Bukti
1. Setelah beberapa screenshot terkumpul, pengguna menekan `Upload Attachments`.
2. Sistem mengupload semua screenshot yang belum terupload.
3. Jika upload berhasil, setiap file mendapat attachment ID terkait.

### 3.5 Submit ke TestRail
1. Pengguna memastikan status result sudah dipilih dengan benar.
2. Pengguna memastikan semua screenshot sudah diupload.
3. Pengguna memastikan durasi kerja sudah > 0.
4. Pengguna menekan `Submit to TestRail`.

## 4. Rule Khusus: Screenshot Tidak Boleh Sebelum Play
Ini adalah aturan bisnis utama yang diminta.

- Jika pengguna mencoba mengambil screenshot sebelum menekan tombol play, sistem harus menolak aksi tersebut.
- Sistem menampilkan pesan peringatan seperti:
  - `Please click the ▶ button in Working Time before adding screenshots or comments here.`
- Tujuan aturan ini:
  - memastikan setiap bukti memiliki konteks waktu pengerjaan yang valid;
  - mencegah hasil test tanpa durasi yang benar;
  - menjaga konsistensi data yang dikirim ke TestRail.

## 5. Contoh Skenario

### Skenario A: Benar
- Pengguna menekan play.
- Timer berjalan.
- Pengguna mengambil screenshot.
- Screenshot berhasil disimpan dan diupload.
- Pengguna submit.

### Skenario B: Salah
- Pengguna langsung mencoba screenshot tanpa menekan play.
- Sistem menolak aksi.
- Pengguna diminta memulai sesi testing terlebih dahulu.

## 6. Ringkasan Inti
- `Play` = memulai sesi testing.
- `Capture` = hanya boleh dilakukan saat sesi berjalan.
- `Upload` = wajib sebelum submit.
- `Submit` = hanya boleh dilakukan jika durasi dan attachment sudah siap.
