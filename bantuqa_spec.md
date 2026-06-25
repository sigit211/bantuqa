# Software Requirements & Technical Specification
## Project: TestRail Desktop Capture Tool (BantuQa)

Dokumen ini berfungsi sebagai spesifikasi teknis dan fungsional untuk pengembangan aplikasi desktop berbasis Windows yang dirancang untuk mempercepat proses pembuatan bukti pengujian (*test evidence*) dan pelaporan hasil eksekusi tes langsung ke platform **TestRail**.

---

## 1. Pendahuluan & Tujuan
Proses dokumentasi *bug* atau *test evidence* secara manual (mengambil screenshot, menyimpan ke lokal, membuka browser, mencari test case, dan mengunggah gambar) membutuhkan waktu yang cukup lama bagi tim Quality Assurance (QA). 

Aplikasi **BantuQa** bertujuan untuk memotong rantai alur kerja tersebut dengan menyediakan perkakas desktop yang ringkas, mendukung pengambilan banyak gambar sekaligus melalui metode *click-and-drag* (seperti Snipping Tool), dan mengotomatisasi proses pelaporan serta pengunggahan lampiran ke TestRail menggunakan TestRail API.

---

## 2. Arsitektur & Perangkat Teknologi (Tech Stack)
Aplikasi ini akan dikembangkan sepenuhnya menggunakan bahasa pemrograman **Python** dengan spesifikasi komponen sebagai berikut:

* **Bahasa Pemrograman:** Python 3.10+
* **Grafis & Antarmuka (GUI):** `CustomTkinter` (untuk visual modern dan mendukung *Dark Mode*) atau `PyQt6`.
* **Pengolahan Gambar:** `Pillow` (PIL) & `mss` (untuk penangkapan layar berkinerja tinggi).
* **Manajemen Hotkey Global:** `pynput` atau `keyboard` (untuk mendeteksi pintasan papan ketik meskipun aplikasi sedang berjalan di latar belakang/*minimized*).
* **Komunikasi API:** `requests` (untuk menangani HTTP Request dengan skema *Basic Authentication*).
* **Keamanan Kredensial:** `keyring` (untuk mengamankan Password/API Key dengan *Credential Manager* bawaan OS).
* **Pengemas Aplikasi:** `PyInstaller` (untuk mengompilasi kode Python menjadi satu file eksekutabel `.exe` standalone sehingga pengguna tidak perlu menginstal Python di komputer mereka).

---

## 3. Spesifikasi Fungsional (User Flow)

### 3.1. Autentikasi Pengguna (Layar Login)
1. Saat aplikasi pertama kali dijalankan, pengguna dihadapkan pada layar login.
2. Pengguna wajib memasukkan:
   * **TestRail URL** (misal: `<https://perusahaan.testrail.io>`)
   * **Email / Username TestRail**
   * **Password / API Key TestRail**
3. Kredensial ini akan digunakan sebagai token *Basic Auth* untuk setiap permintaan API.
4. Aplikasi akan memvalidasi kredensial dengan melakukan *ping* ke API `get_user_by_email`. Jika sukses (HTTP 200), kredensial disimpan secara aman di sistem OS menggunakan library `keyring` (bukan dalam bentuk teks biasa/*plaintext*), sehingga pengguna tidak perlu login berulang kali setelah komputer di-restart. Pengguna kemudian diarahkan ke mode *standby*.

### 3.2. Mode Siaga & Aktivasi Capture (Snipping Tool Style)
1. Aplikasi berjalan secara pasif di *system tray* atau diminimalkan.
2. Pengguna mengaktifkan fitur *capture* menggunakan *Global Hotkey* (Contoh: `Ctrl + Shift + S`).
3. **Alur Snipping Area:**
   * Aplikasi mengambil snapshot seluruh layar penuh/seluruh monitor yang digunakan (*full screen* mencakup seluruh area monitor yang aktif) di latar belakang (*background*).
   * Muncul jendela kanvas transparan penuh layar (Overlay) dengan tingkat kegelapan tertentu (Opacity ~30%).
   * **Mouse Click Down ($X_1, Y_1$):** Menentukan titik awal area.
   * **Mouse Dragging:** Menampilkan kotak indikator persegi dengan garis putus-putus secara dinamis.
   * **Mouse Release ($X_2, Y_2$):** Jendela overlay tertutup, aplikasi melakukan *cropping* pada gambar *background* berdasarkan koordinat terpilih.
4. **Anotasi Gambar (Opsional):** Setelah di-*crop*, dapat ditampilkan panel anotasi minimalis (kuas, kotak penanda, atau panah) untuk menyoroti *bug* secara presisi.
5. Gambar yang berhasil dipotong dimasukkan ke dalam **"Keranjang Screenshot" (Temporary Queue)** di dalam memori aplikasi.
6. Pengguna dapat mengulangi proses *capture* ini berkali-kali tanpa terganggu oleh pop-up pengisian data.

### 3.3. Formulir Submit (Dashboard Kecil)
Setelah pengguna memberikan URL, email, dan password pada saat login, dan selesai mengambil semua screenshot yang diperlukan, maka akan muncul antarmuka berupa *dashboard* kecil untuk memproses data.

1. **Panel Pratinjau (Preview) & Hapus:** Menampilkan *thumbnail* gambar-gambar yang sudah ditangkap di dalam "Keranjang". Terdapat tombol (X) di tiap *thumbnail* agar pengguna bisa membuang/menghapus gambar yang salah tangkap sebelum di-submit.
2. **Caching & State Persistence (Mengingat Pilihan Terakhir):** Aplikasi akan secara otomatis menyimpan pilihan terakhir untuk *Project*, *Test Plan*, dan *Test Run* yang digunakan. Hal ini sangat berguna karena QA seringkali fokus di *Test Run* yang sama berjam-jam sehingga tak perlu memilih ulang *dropdown*.
3. **Memilih Project:** Aplikasi akan memuat daftar proyek melalui API `get_projects`. Pengguna kemudian memilih proyek yang dituju (jika berbeda dari *cache*).
4. **Memilih Test Plan / Test Run & Tombol Refresh:**
   * Pengguna diberikan pilihan untuk menelusuri berdasarkan **Test Plan** atau langsung memilih **Test Run**.
   * Jika pengguna memilih **Test Plan**, aplikasi akan memuat daftar Test Run yang berada di dalam Test Plan tersebut, lalu pengguna dapat memilih Test Run spesifik.
   * Jika pengguna memilih **Test Run**, aplikasi langsung memuat daftar Test Run independen dan pengguna memilih dari daftar tersebut.
   * Disediakan **Tombol Refresh** di sebelah pilihan Test Plan/Test Run untuk memuat ulang daftar data terbaru (mengambil Test Plan atau Test Run yang baru saja ditambahkan di TestRail).
5. **Memilih Test Case:** Setelah Test Run ditentukan, pengguna tidak perlu memasukkan Test Case ID secara manual. Aplikasi akan memuat daftar Test Case (Tests) yang ada di dalam Test Run tersebut ke dalam *dropdown*, dan pengguna cukup memilih Test Case dari daftar tersebut.
6. **Memilih Status Testing:** Pengguna memilih status akhir eksekusi (seperti `Passed` atau `Failed`).
7. **Kotak Komentar (Opsional):** Tersedia *text area* bagi pengguna untuk mengetik catatan atau komentar hasil pengujian. Jika dibiarkan kosong, maka *comment* nantinya murni hanya berisi lampiran gambar.
8. **Tombol Upload Attachment:** Jika terdapat satu atau lebih screenshot di *keranjang*, pengguna harus menekan tombol **Upload Attachments** sebelum menekan tombol **Submit to TestRail**. Tombol ini akan mengunggah seluruh file screenshot ke *TestRail run* yang dipilih, mencatat setiap `attachment_id` dari hasil upload, dan menampilkan daftar `attachment_id` tersebut dalam bentuk markdown siap pakai.
   * Setiap file yang berhasil diunggah akan disimpan dengan `attachment_id` terkait.
   * Aplikasi menampilkan string markdown `![](index.php?/attachments/get/{attachment_id})` untuk setiap attachment yang telah diupload.
   * Tombol **Submit to TestRail** hanya aktif jika tidak ada attachment yang belum diupload.
9. **Tombol Start/Stop/Hold Testing:** Aplikasi menyediakan tombol **Start Testing** untuk memulai sesi pengujian, serta tombol **Hold Testing** dan **Stop Testing** untuk menghentikan atau mengakhiri waktu.
   * Ketika **Start Testing** ditekan, aplikasi mencatat waktu mulai dan memicu proses screenshot ketika pengguna menggunakan *hotkey* `Ctrl + Shift + S`.
   * Setelah **Start Testing** ditekan, tombol **Hold Testing** dan **Stop Testing** akan muncul, sementara tombol **Start Testing** dinonaktifkan.
   * Ketika **Hold Testing** ditekan, penghitung waktu _pause_ dan durasi yang sudah berjalan dipertahankan, tanpa mengakhiri sesi pengujian.
   * Ketika **Stop Testing** ditekan, sesi screenshot berakhir dan aplikasi mencatat durasi pengujian total dalam satuan detik.
   * Durasi yang dicatat akan digunakan sebagai nilai `elapsed` pada payload `add_result_for_case`.
10. **Tombol Sign Out / Logout:** Disediakan opsi atau tombol untuk keluar dari sesi saat ini. Menekan tombol ini akan menghapus atau membersihkan kredensial yang tersimpan di memori OS (`keyring`) dan mengembalikan pengguna ke **Layar Login**.

---

## 4. Alur Integrasi API TestRail (Technical Workflow)

Proses pengunggahan ke TestRail harus dilakukan secara sekuensial menggunakan urutan API berikut:

### Langkah 1: Autentikasi & Validasi Awal
Setiap HTTP Request wajib menyertakan *Header Basic Auth* menggunakan kombinasi Email dan Password/API Key yang telah ditarik secara aman dari memori `keyring`.

### Langkah 2: Mengambil Data Hierarki Proyek & Daftar Test Case
* **Get Projects:** ``GET /index.php`?`/api/v2/get_projects`` untuk menampilkan pilihan *Project*.
* **Get Plans:** ``GET /index.php`?`/api/v2/get_plans`/{project_id}` jika pengguna memilih alur pencarian melalui Test Plan.
* **Get Plan Details (Mencari Test Run):** ``GET /index.php`?`/api/v2/get_plan`/{plan_id}` untuk melihat daftar Test Run (runs) yang terdapat di dalam Test Plan yang dipilih pengguna.
* **Get Runs:** ``GET /index.php`?`/api/v2/get_runs`/{project_id}` untuk langsung mendapatkan daftar Test Run independen yang tidak berada di dalam plan tertentu.
* **Get Tests:** ``GET /index.php`?`/api/v2/get_tests`/{run_id}` untuk memuat daftar Test Case (Tests) pada Test Run yang dipilih dan menampilkannya di *dropdown* pemilihan Test Case.

### Langkah 3: Mengunggah Screenshot ke Test Run (Attachment)
Setiap screenshot yang telah ditangkap (*capture*) tidak akan langsung dilampirkan ke hasil test case, melainkan diunggah ke Test Run.
* **Endpoint API:** ``POST /index.php`?`/api/v2/add_attachment_to_run`/{run_id}`
* **Payload:** *File gambar*
* **Response:** TestRail akan mengembalikan JSON berisi informasi attachment, termasuk `attachment_id`.
* **Proses:** Jika terdapat lebih dari satu screenshot, aplikasi akan melakukan *loop* pengunggahan satu per satu dan mencatat (menyimpan) seluruh `attachment_id` yang dihasilkan.

### Langkah 4: Memasukkan Hasil Uji dan Komentar Screenshot (Add Result for Case)
Setelah seluruh proses unggah gambar selesai dan id-nya terkumpul, langkah terakhir adalah mengirimkan status pengujian beserta komentar yang memuat gambar.
* **Endpoint API:** ``POST /index.php`?`/api/v2/add_result_for_case`/{run_id}/{case_id}`
* **Payload JSON:** Aplikasi mengirimkan payload berisi `status_id` (contoh: 1 untuk *Passed*, 5 untuk *Failed*) dan `comment`.
* **Format Komentar (Teks & Markdown Gambar):**
  Aplikasi akan menyusun teks pada payload `comment` berdasarkan masukan dari **Kotak Komentar** di *dashboard*. Jika pengguna mengisi komentar, teks tersebut akan diletakkan di bagian atas, lalu diikuti oleh sintaks Markdown TestRail untuk gambar. Jika kotak komentar dibiarkan kosong, maka isinya murni hanya urutan gambar.
  
  **Aturan Urutan Gambar:** Kumpulan `attachment_id` yang dicatat dari Langkah 3 akan dirangkai menjadi `![](index.php?/attachments/get/{attachment_id})`. Jika ada lebih dari satu screenshot, markdown gambar akan disusun **memanjang ke bawah**. Screenshot pertama (paling awal ditangkap) berada di urutan teratas, diikuti screenshot kedua di bawahnya, dan seterusnya.

  **Contoh Komentar JSON (Dengan teks pengguna):**
  Pastikan bahwa *markdown* gambar benar-benar digabungkan ke dalam payload `comment` saat di-*submit* agar gambar tampil pada TestRail, bukan hanya teks komentarnya saja.
  ```json
  {
    "status_id": 1,
    "comment": "Terdapat bug pada bagian tombol login yang tidak responsif saat ditekan dua kali.\n\n![](index.php?/attachments/get/12345)\n![](index.php?/attachments/get/12346)"
  }
  ```

  **Contoh Komentar JSON (Kosong/Tanpa teks pengguna):**
  ```json
  {
    "status_id": 1,
    "comment": "![](index.php?/attachments/get/12345)"
  }
