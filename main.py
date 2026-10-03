import csv
import hashlib
import sqlite3
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import ttk, messagebox, filedialog

# matplotlib dipakai buat grafik, kalau belum diinstall programnya tetap jalan
try:
    import matplotlib.pyplot as plt
    ADA_MATPLOTLIB = True
except ImportError:
    ADA_MATPLOTLIB = False


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "smart_retail.db"
STRUK_DIR = BASE_DIR / "struk"
BATAS_STOK_MENIPIS = 10

PINK = "#d63384"
PINK_MUDA = "#ffe6f2"
PINK_SEDANG = "#ffc2e0"
PUTIH = "#ffffff"
ABU = "#666666"
MERAH = "#c0392b"
HIJAU = "#2e7d32"

FONT = ("Arial", 10)
FONT_BOLD = ("Arial", 10, "bold")
FONT_JUDUL = ("Arial", 13, "bold")

DISKON_BELANJA = [
    (500000, 5),
    (250000, 3),
    (100000, 2),
]

LEVEL_MEMBER = [
    (3000000, "Platinum", 3),
    (1000000, "Gold", 2),
    (0, "Silver", 1),
]

RUPIAH_PER_POIN = 10000

HARI = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]

CSV_DELIMITER = ";"

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('admin', 'kasir'))
);

CREATE TABLE IF NOT EXISTS produk (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nama_produk TEXT NOT NULL,
    harga_modal INTEGER NOT NULL CHECK (harga_modal >= 0),
    harga_jual INTEGER NOT NULL CHECK (harga_jual >= 0),
    stok INTEGER NOT NULL CHECK (stok >= 0)
);

CREATE TABLE IF NOT EXISTS transaksi (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tanggal TEXT NOT NULL,
    total_bayar INTEGER NOT NULL,
    uang_diterima INTEGER NOT NULL,
    kembalian INTEGER NOT NULL,
    kasir TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS detail_transaksi (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_transaksi INTEGER NOT NULL,
    id_produk INTEGER NOT NULL,
    jumlah INTEGER NOT NULL CHECK (jumlah > 0),
    subtotal INTEGER NOT NULL,
    FOREIGN KEY (id_transaksi) REFERENCES transaksi(id),
    FOREIGN KEY (id_produk) REFERENCES produk(id)
);
"""

KOLOM_BARU_TRANSAKSI = [
    ("subtotal", "INTEGER NOT NULL DEFAULT 0"),
    ("diskon_belanja", "INTEGER NOT NULL DEFAULT 0"),
    ("diskon_member", "INTEGER NOT NULL DEFAULT 0"),
    ("id_member", "INTEGER REFERENCES member(id)"),
    ("poin_didapat", "INTEGER NOT NULL DEFAULT 0"),
]

USER_AWAL = [
    ("admin", "5678", "admin"),
    ("kasir", "1234", "kasir"),
]

PRODUK_AWAL = [
    ("Indomie Goreng", 2900, 3500, 30),
    ("Indomie Kuah", 2900, 3500, 30),
    ("Beras 5 Kg", 68000, 75000, 10),
    ("Minyak Goreng 1L", 16000, 18000, 20),
    ("Gula 1 Kg", 15000, 17000, 20),
    ("Telur 1 Kg", 27000, 30000, 15),
    ("Aqua 600ml", 3000, 4000, 40),
    ("Teh Botol", 3800, 5000, 30),
    ("Kopi Sachet", 2000, 2500, 40),
    ("Rokok", 23000, 25000, 20),
]


def rupiah(angka):
    return "Rp{:,.0f}".format(angka).replace(",", ".")


def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def format_tanggal(tanggal_db):
    try:
        dt = datetime.strptime(tanggal_db, "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%d/%m/%Y %H:%M")
    except ValueError:
        return tanggal_db


def format_tanggal_pendek(tanggal_db):
    try:
        dt = datetime.strptime(tanggal_db, "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%d/%m/%Y")
    except ValueError:
        return tanggal_db


def normalisasi_telepon(teks):
    hasil = ""
    for huruf in teks:
        if huruf not in " -+()":
            hasil = hasil + huruf
    return hasil


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def migrasi_db(conn):
    kolom_ada = []
    for r in conn.execute("PRAGMA table_info(transaksi)"):
        kolom_ada.append(r["name"])

    for nama, definisi in KOLOM_BARU_TRANSAKSI:
        if nama not in kolom_ada:
            conn.execute("ALTER TABLE transaksi ADD COLUMN " + nama + " " + definisi)

    conn.execute(
        "UPDATE transaksi SET subtotal = total_bayar "
        "WHERE subtotal = 0 AND diskon_belanja = 0 AND diskon_member = 0"
    )


def init_db():
    conn = get_conn()
    try:
        conn.executescript(SCHEMA)
        migrasi_db(conn)

        jumlah_user = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if jumlah_user == 0:
            for username, password, role in USER_AWAL:
                conn.execute(
                    "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                    (username, hash_password(password), role),
                )

        jumlah_produk = conn.execute("SELECT COUNT(*) FROM produk").fetchone()[0]
        if jumlah_produk == 0:
            conn.executemany(
                "INSERT INTO produk (nama_produk, harga_modal, harga_jual, stok) "
                "VALUES (?, ?, ?, ?)",
                PRODUK_AWAL,
            )

        conn.commit()
    finally:
        conn.close()


def query_all(sql, params=()):
    conn = get_conn()
    try:
        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()


def query_one(sql, params=()):
    conn = get_conn()
    try:
        return conn.execute(sql, params).fetchone()
    finally:
        conn.close()


def execute(sql, params=()):
    conn = get_conn()
    try:
        conn.execute(sql, params)
        conn.commit()
    finally:
        conn.close()


def cek_login(username, password):
    row = query_one(
        "SELECT role FROM users WHERE username = ? AND password = ?",
        (username, hash_password(password)),
    )
    if row:
        return row["role"]
    return None


def ambil_produk(keyword=""):
    keyword = keyword.strip()

    if keyword == "":
        return query_all("SELECT * FROM produk ORDER BY id")
    elif keyword.isdigit():
        return query_all(
            "SELECT * FROM produk WHERE id = ? OR nama_produk LIKE ? ORDER BY id",
            (int(keyword), "%" + keyword + "%"),
        )
    else:
        return query_all(
            "SELECT * FROM produk WHERE nama_produk LIKE ? ORDER BY id",
            ("%" + keyword + "%",),
        )


def tambah_produk(nama, modal, jual, stok):
    execute(
        "INSERT INTO produk (nama_produk, harga_modal, harga_jual, stok) "
        "VALUES (?, ?, ?, ?)",
        (nama, modal, jual, stok),
    )


def ubah_produk(id_produk, nama, modal, jual, stok):
    execute(
        "UPDATE produk SET nama_produk = ?, harga_modal = ?, "
        "harga_jual = ?, stok = ? WHERE id = ?",
        (nama, modal, jual, stok, id_produk),
    )


def hapus_produk(id_produk):
    try:
        execute("DELETE FROM produk WHERE id = ?", (id_produk,))
        return True, "Produk berhasil dihapus."
    except sqlite3.IntegrityError:
        return False, (
            "Produk tidak bisa dihapus karena sudah ada di riwayat transaksi.\n"
            "Ubah stoknya menjadi 0 jika produk tidak dijual lagi."
        )


def level_member(total_belanja):
    for batas, nama, persen in LEVEL_MEMBER:
        if total_belanja >= batas:
            return nama, persen
    return LEVEL_MEMBER[-1][1], LEVEL_MEMBER[-1][2]


def hitung_diskon(subtotal, member=None):
    persen_belanja = 0
    i = 0
    while i < len(DISKON_BELANJA):
        batas, persen = DISKON_BELANJA[i]
        if subtotal >= batas:
            persen_belanja = persen
            break
        i = i + 1
    diskon_belanja = subtotal * persen_belanja // 100

    level = None
    persen_member = 0
    if member is not None:
        level, persen_member = level_member(member["total_belanja"])
    diskon_member = subtotal * persen_member // 100

    total = subtotal - diskon_belanja - diskon_member

    if member is not None:
        poin = total // RUPIAH_PER_POIN
    else:
        poin = 0

    return {
        "subtotal": subtotal,
        "persen_belanja": persen_belanja,
        "diskon_belanja": diskon_belanja,
        "level": level,
        "persen_member": persen_member,
        "diskon_member": diskon_member,
        "total": total,
        "poin": poin,
    }


def info_diskon_berikutnya(subtotal):
    for batas, persen in sorted(DISKON_BELANJA):
        if subtotal < batas:
            return batas - subtotal, persen
    return None


def teks_aturan():
    daftar_diskon = []
    for batas, persen in sorted(DISKON_BELANJA):
        daftar_diskon.append("mulai " + rupiah(batas) + " = " + str(persen) + "%")

    daftar_level = []
    for batas, nama, persen in sorted(LEVEL_MEMBER):
        if batas > 0:
            daftar_level.append(nama + " (akumulasi " + rupiah(batas) + ") = +" + str(persen) + "%")
        else:
            daftar_level.append(nama + " (member baru) = +" + str(persen) + "%")

    teks = "Diskon belanja otomatis :  " + "  |  ".join(daftar_diskon) + "\n"
    teks += "Diskon tambahan member  :  " + "  |  ".join(daftar_level) + "\n"
    teks += "Poin member             :  1 poin setiap belanja " + rupiah(RUPIAH_PER_POIN)
    teks += " (dihitung setelah diskon)"
    return teks


def cari_member(keyword=""):
    keyword = keyword.strip()
    if keyword == "":
        return query_all("SELECT * FROM member ORDER BY id")
    like = "%" + keyword + "%"
    return query_all(
        "SELECT * FROM member WHERE kode LIKE ? OR nama LIKE ? "
        "OR telepon LIKE ? ORDER BY id",
        (like, like, like),
    )


def temukan_member(keyword):
    keyword = keyword.strip()
    if keyword == "":
        return None
    row = query_one("SELECT * FROM member WHERE kode = ?", (keyword.upper(),))
    if row is None:
        row = query_one("SELECT * FROM member WHERE telepon = ?",
                        (normalisasi_telepon(keyword),))
    return row


def ambil_member_by_id(id_member):
    if id_member is None:
        return None
    return query_one("SELECT * FROM member WHERE id = ?", (id_member,))


def tambah_member(nama, telepon):
    conn = get_conn()
    try:
        tanggal = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur = conn.execute(
            "INSERT INTO member (nama, telepon, tanggal_daftar) VALUES (?, ?, ?)",
            (nama, telepon, tanggal),
        )
        id_member = cur.lastrowid
        kode = "M" + str(id_member).zfill(4)
        conn.execute("UPDATE member SET kode = ? WHERE id = ?", (kode, id_member))
        conn.commit()
        return id_member
    except sqlite3.IntegrityError:
        conn.rollback()
        raise ValueError("Nomor HP sudah terdaftar sebagai member.")
    finally:
        conn.close()


def ubah_member(id_member, nama, telepon):
    try:
        execute("UPDATE member SET nama = ?, telepon = ? WHERE id = ?",
                (nama, telepon, id_member))
    except sqlite3.IntegrityError:
        raise ValueError("Nomor HP sudah dipakai member lain.")


def hapus_member(id_member):
    try:
        execute("DELETE FROM member WHERE id = ?", (id_member,))
        return True, "Member berhasil dihapus."
    except sqlite3.IntegrityError:
        return False, "Member tidak bisa dihapus karena sudah ada di riwayat transaksi."


def simpan_transaksi(keranjang, uang_bayar, kasir, id_member=None):
    conn = get_conn()
    try:
        items = []
        subtotal_belanja = 0

        for id_produk, jumlah in keranjang.items():
            row = conn.execute(
                "SELECT nama_produk, harga_jual, stok FROM produk WHERE id = ?",
                (id_produk,),
            ).fetchone()

            if row is None:
                raise ValueError("Ada produk di keranjang yang sudah dihapus.")

            if jumlah > row["stok"]:
                raise ValueError(
                    "Stok tidak mencukupi.\n"
                    "Stok " + row["nama_produk"] + " tersisa " + str(row["stok"]) + ".\n"
                    "Silakan masukkan jumlah yang lebih kecil."
                )

            subtotal = row["harga_jual"] * jumlah
            subtotal_belanja += subtotal
            items.append((id_produk, row["nama_produk"], jumlah,
                          row["harga_jual"], subtotal))

        member = None
        if id_member is not None:
            member = conn.execute(
                "SELECT * FROM member WHERE id = ?", (id_member,)
            ).fetchone()
            if member is None:
                raise ValueError("Data member tidak ditemukan.")

        diskon = hitung_diskon(subtotal_belanja, member)
        total = diskon["total"]

        if uang_bayar < total:
            raise ValueError("Uang pembayaran kurang " + rupiah(total - uang_bayar) + ".")

        kembalian = uang_bayar - total
        tanggal = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if member:
            id_member_simpan = member["id"]
        else:
            id_member_simpan = None

        cur = conn.execute(
            "INSERT INTO transaksi (tanggal, total_bayar, uang_diterima, "
            "kembalian, kasir, subtotal, diskon_belanja, diskon_member, "
            "id_member, poin_didapat) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (tanggal, total, uang_bayar, kembalian, kasir,
             subtotal_belanja, diskon["diskon_belanja"],
             diskon["diskon_member"], id_member_simpan, diskon["poin"]),
        )
        id_transaksi = cur.lastrowid

        for id_produk, nama, jumlah, harga, subtotal in items:
            conn.execute(
                "INSERT INTO detail_transaksi (id_transaksi, id_produk, jumlah, subtotal) "
                "VALUES (?, ?, ?, ?)",
                (id_transaksi, id_produk, jumlah, subtotal),
            )
            conn.execute(
                "UPDATE produk SET stok = stok - ? WHERE id = ?",
                (jumlah, id_produk),
            )

        info_member = None
        if member is not None:
            conn.execute(
                "UPDATE member SET poin = poin + ?, "
                "total_belanja = total_belanja + ? WHERE id = ?",
                (diskon["poin"], total, member["id"]),
            )
            info_member = {
                "id": member["id"],
                "kode": member["kode"],
                "nama": member["nama"],
                "level": diskon["level"],
                "poin_didapat": diskon["poin"],
                "poin_total": member["poin"] + diskon["poin"],
            }

        conn.commit()

        return {
            "id": id_transaksi,
            "tanggal": tanggal,
            "kasir": kasir,
            "items": items,
            "subtotal": subtotal_belanja,
            "persen_belanja": diskon["persen_belanja"],
            "diskon_belanja": diskon["diskon_belanja"],
            "persen_member": diskon["persen_member"],
            "diskon_member": diskon["diskon_member"],
            "member": info_member,
            "total": total,
            "bayar": uang_bayar,
            "kembalian": kembalian,
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def ambil_riwayat():
    return query_all(
        "SELECT t.*, m.nama AS nama_member, m.kode AS kode_member "
        "FROM transaksi t LEFT JOIN member m ON m.id = t.id_member "
        "ORDER BY t.id DESC"
    )


def ambil_transaksi(id_transaksi):
    return query_one(
        "SELECT t.*, m.nama AS nama_member, m.kode AS kode_member "
        "FROM transaksi t LEFT JOIN member m ON m.id = t.id_member "
        "WHERE t.id = ?",
        (id_transaksi,),
    )


def ambil_detail_transaksi(id_transaksi):
    return query_all(
        "SELECT p.nama_produk, d.jumlah, d.subtotal, "
        "d.subtotal / d.jumlah AS harga "
        "FROM detail_transaksi d "
        "JOIN produk p ON p.id = d.id_produk "
        "WHERE d.id_transaksi = ? ORDER BY d.id",
        (id_transaksi,),
    )


def ambil_laporan():
    ringkasan = query_one(
        "SELECT COUNT(*) AS jumlah, COALESCE(SUM(total_bayar), 0) AS pendapatan "
        "FROM transaksi"
    )
    terlaris = query_one(
        "SELECT p.nama_produk, SUM(d.jumlah) AS terjual "
        "FROM detail_transaksi d "
        "JOIN produk p ON p.id = d.id_produk "
        "GROUP BY p.id ORDER BY terjual DESC LIMIT 1"
    )
    menipis = query_all(
        "SELECT nama_produk, stok FROM produk WHERE stok < ? ORDER BY stok",
        (BATAS_STOK_MENIPIS,),
    )
    diskon = query_one(
        "SELECT COALESCE(SUM(diskon_belanja + diskon_member), 0) AS total "
        "FROM transaksi"
    )
    member = query_one("SELECT COUNT(*) AS jumlah FROM member")
    return {
        "jumlah_transaksi": ringkasan["jumlah"],
        "pendapatan": ringkasan["pendapatan"],
        "terlaris": terlaris,
        "menipis": menipis,
        "total_diskon": diskon["total"],
        "jumlah_member": member["jumlah"],
    }


def rata_kiri_kanan(kiri, kanan):
    sisa = 32 - len(kiri)
    if sisa > len(kanan):
        return kiri + kanan.rjust(sisa)
    return kiri + " " + kanan


def buat_struk(hasil):
    garis_dua = "=" * 32
    garis_satu = "-" * 32
    tgl = format_tanggal(hasil["tanggal"])
    member = hasil.get("member")

    baris = [
        garis_dua,
        "SMART RETAIL".center(32),
        garis_dua,
        "No Transaksi : " + str(hasil["id"]),
        "Tanggal      : " + tgl,
        "Kasir        : " + hasil["kasir"],
    ]
    if member:
        baris.append("Member       : " + member["nama"][:14] + " (" + member["kode"] + ")")
        baris.append("Level        : " + member["level"])
    baris.append(garis_satu)

    for _, nama, jumlah, harga, _ in hasil["items"]:
        kiri = nama[:16].ljust(16)
        kanan = str(jumlah) + " x " + str(harga)
        baris.append((kiri + " " + kanan).rstrip())

    baris.append(garis_satu)

    if hasil.get("diskon_belanja", 0) or hasil.get("diskon_member", 0):
        baris.append(rata_kiri_kanan("Subtotal", rupiah(hasil["subtotal"])))
        if hasil["diskon_belanja"]:
            baris.append(rata_kiri_kanan(
                "Diskon belanja " + str(hasil["persen_belanja"]) + "%",
                "-" + rupiah(hasil["diskon_belanja"])))
        if hasil["diskon_member"]:
            baris.append(rata_kiri_kanan(
                "Diskon member " + str(hasil["persen_member"]) + "%",
                "-" + rupiah(hasil["diskon_member"])))
        baris.append(garis_satu)

    baris.append("TOTAL     = " + rupiah(hasil["total"]))
    baris.append("BAYAR     = " + rupiah(hasil["bayar"]))
    baris.append("KEMBALIAN = " + rupiah(hasil["kembalian"]))

    if member:
        baris.append(garis_satu)
        baris.append("Poin didapat : +" + str(member["poin_didapat"]))
        baris.append("Total poin   : " + str(member["poin_total"]))

    baris.append(garis_dua)
    baris.append("Terima kasih".center(32))
    return "\n".join(baris)


def simpan_struk_txt(hasil, teks_struk):
    STRUK_DIR.mkdir(exist_ok=True)
    nama_file = "struk_" + str(hasil["id"]).zfill(5) + ".txt"
    path = STRUK_DIR / nama_file
    path.write_text(teks_struk, encoding="utf-8")
    return path


def export_laporan_csv(path):
    rows = query_all(
        "SELECT t.id AS no_transaksi, t.tanggal, t.kasir, p.nama_produk, "
        "d.jumlah, d.subtotal / d.jumlah AS harga, d.subtotal, t.total_bayar, "
        "(t.diskon_belanja + t.diskon_member) AS diskon, "
        "COALESCE(m.nama, '-') AS member "
        "FROM transaksi t "
        "JOIN detail_transaksi d ON d.id_transaksi = t.id "
        "JOIN produk p ON p.id = d.id_produk "
        "LEFT JOIN member m ON m.id = t.id_member "
        "ORDER BY t.id, d.id"
    )
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter=CSV_DELIMITER)
        writer.writerow(["No Transaksi", "Tanggal", "Kasir", "Produk",
                         "Jumlah", "Harga Satuan", "Subtotal",
                         "Total Transaksi", "Diskon Transaksi", "Member"])
        for r in rows:
            writer.writerow([r["no_transaksi"], r["tanggal"], r["kasir"],
                             r["nama_produk"], r["jumlah"], r["harga"],
                             r["subtotal"], r["total_bayar"], r["diskon"],
                             r["member"]])
    return len(rows)


window = None       
frame_isi = None     
lbl_jam = None
job_jam = None

user_login = ""
role_login = ""
keranjang = {}           
member_aktif_id = None  

ent_user = None
ent_pass = None
var_lihat_pass = None

var_cari_produk = None
tree_produk = None
lbl_jumlah_produk = None

var_cari_menu = None
tree_cari = None
lbl_jumlah_cari = None

var_cari_kasir = None
tree_kasir = None
spin_jumlah = None
tree_keranjang = None
lbl_jumlah_item = None
var_member = None
lbl_member = None
lbl_subtotal = None
lbl_diskon_belanja = None
lbl_diskon_member = None
lbl_total = None
lbl_hint_diskon = None
var_bayar = None
lbl_kembalian = None

lbl_jml_transaksi = None
lbl_pendapatan = None
lbl_total_diskon = None
lbl_jml_member = None
lbl_terlaris = None
lbl_terjual = None
list_menipis = None

win_riwayat = None
tree_riwayat = None

var_cari_member = None
tree_member = None
lbl_jumlah_member = None


def ada(widget):
    if widget is None:
        return False
    try:
        return bool(widget.winfo_exists())
    except tk.TclError:
        return False


def buat_tombol(parent, teks, perintah, warna=None):
    tombol = tk.Button(parent, text=teks, command=perintah, font=FONT, padx=8, pady=2)
    if warna is not None:
        tombol.config(bg=warna, fg=PUTIH, activebackground=warna,
                      activeforeground=PUTIH)
    return tombol


def buat_tabel(parent, kolom, tinggi=12):
    frame = tk.Frame(parent)
    nama_kolom = []
    for k in kolom:
        nama_kolom.append(k[0])

    tree = ttk.Treeview(frame, columns=nama_kolom, show="headings",
                        height=tinggi, selectmode="browse")
    for key, judul, lebar, rata in kolom:
        tree.heading(key, text=judul)
        tree.column(key, width=lebar, anchor=rata)

    tree.tag_configure("menipis", foreground=MERAH)

    scroll = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scroll.set)
    scroll.pack(side="right", fill="y")
    tree.pack(side="left", fill="both", expand=True)
    return frame, tree


def kosongkan_tabel(tree):
    for item in tree.get_children():
        tree.delete(item)


def tambah_baris(tree, nilai, iid=None, tags=()):
    if iid is None:
        tree.insert("", "end", values=nilai, tags=tags)
    else:
        tree.insert("", "end", iid=str(iid), values=nilai, tags=tags)


def bersihkan_window():
    global job_jam
    if job_jam is not None:
        try:
            window.after_cancel(job_jam)
        except tk.TclError:
            pass
        job_jam = None
    for widget in window.winfo_children():
        widget.destroy()


def bersihkan_isi():
    for widget in frame_isi.winfo_children():
        widget.destroy()


def tengahkan(win):
    win.update_idletasks()
    w = win.winfo_reqwidth()
    h = win.winfo_reqheight()
    x = window.winfo_rootx() + (window.winfo_width() - w) // 2
    y = window.winfo_rooty() + (window.winfo_height() - h) // 2
    win.geometry("+" + str(max(x, 0)) + "+" + str(max(y, 0)))


def buat_dialog(judul):
    win = tk.Toplevel(window)
    win.title(judul)
    win.transient(window)
    win.resizable(False, False)
    return win


def aktifkan_dialog(win):
    tengahkan(win)
    try:
        win.grab_set()
    except tk.TclError:
        pass


def bar_atas(judul):
    bar = tk.Frame(frame_isi)
    bar.pack(fill="x", padx=10, pady=(10, 5))
    tk.Button(bar, text="<< Kembali ke Menu", font=FONT,
              command=halaman_menu).pack(side="left")
    tk.Label(bar, text=judul, font=FONT_JUDUL).pack(side="left", padx=15)


def tampilkan_login():
    global ent_user, ent_pass, var_lihat_pass
    global user_login, role_login, keranjang, member_aktif_id

    bersihkan_window()
    user_login = ""
    role_login = ""
    keranjang = {}
    member_aktif_id = None

    kotak = tk.Frame(window)
    kotak.place(relx=0.5, rely=0.45, anchor="center")

    tk.Label(kotak, text="SMART RETAIL", font=("Arial", 24, "bold"),
             fg=PINK).pack()
    tk.Label(kotak, text="Aplikasi Kasir Pintar by Toko Sembako Imut",
             font=FONT).pack(pady=(0, 15))

    form = tk.LabelFrame(kotak, text=" Login ", font=FONT_BOLD, padx=25, pady=15)
    form.pack()

    tk.Label(form, text="Username", font=FONT).grid(row=0, column=0, sticky="w", pady=5)
    ent_user = tk.Entry(form, font=("Arial", 11), width=25)
    ent_user.grid(row=0, column=1, padx=(10, 0), pady=5)

    tk.Label(form, text="Password", font=FONT).grid(row=1, column=0, sticky="w", pady=5)
    ent_pass = tk.Entry(form, font=("Arial", 11), width=25, show="*")
    ent_pass.grid(row=1, column=1, padx=(10, 0), pady=5)

    var_lihat_pass = tk.BooleanVar(value=False)
    tk.Checkbutton(form, text="Tampilkan password", font=FONT,
                   variable=var_lihat_pass,
                   command=ganti_tampilan_password).grid(
        row=2, column=1, sticky="w", padx=(10, 0))

    buat_tombol(form, "LOGIN", proses_login, PINK).grid(
        row=3, column=0, columnspan=2, sticky="ew", pady=(12, 0))

    tk.Label(kotak, text="Admin: admin / 5678   |   Kasir: kasir / 1234",
             font=("Arial", 9), fg=ABU).pack(pady=(12, 0))

    ent_user.focus()
    window.bind("<Return>", lambda e: proses_login())


def ganti_tampilan_password():
    if var_lihat_pass.get():
        ent_pass.config(show="")
    else:
        ent_pass.config(show="*")


def proses_login():
    global user_login, role_login

    username = ent_user.get().strip()
    password = ent_pass.get().strip()

    if username == "" or password == "":
        messagebox.showwarning("Login", "Username dan password wajib diisi!")
        return

    role = cek_login(username, password)

    if role == "admin":
        user_login = username
        role_login = "admin"
    elif role == "kasir":
        user_login = username
        role_login = "kasir"
    else:
        messagebox.showerror("Login Gagal", "Username atau password salah!")
        return

    window.unbind("<Return>")
    tampilkan_main()


def logout():
    if messagebox.askyesno("Logout", "Yakin ingin logout?"):
        tampilkan_login()


def tampilkan_main():
    global frame_isi, lbl_jam

    bersihkan_window()

    header = tk.Frame(window, bg=PINK, height=50)
    header.pack(fill="x")
    header.pack_propagate(False)
    tk.Label(header, text="SMART RETAIL - Toko Sembako Imut",
             font=("Arial", 14, "bold"), bg=PINK, fg=PUTIH).pack(side="left", padx=15)
    tk.Label(header, text="Login: " + user_login + " (" + role_login + ")",
             font=FONT, bg=PINK, fg=PUTIH).pack(side="right", padx=15)

    status = tk.Frame(window, bd=1, relief="sunken")
    status.pack(side="bottom", fill="x")
    tk.Label(status, font=("Arial", 9), fg=ABU,
             text="Diskon otomatis aktif berdasarkan total belanja dan level member"
             ).pack(side="left", padx=10)
    lbl_jam = tk.Label(status, font=("Arial", 9, "bold"))
    lbl_jam.pack(side="right", padx=10)
    update_jam()

    frame_isi = tk.Frame(window)
    frame_isi.pack(fill="both", expand=True)

    halaman_menu()


def update_jam():
    global job_jam
    if not ada(lbl_jam):
        return
    sekarang = datetime.now()
    lbl_jam.config(text=HARI[sekarang.weekday()] + ", " +
                   sekarang.strftime("%d/%m/%Y   %H:%M:%S"))
    job_jam = window.after(1000, update_jam)


def halaman_menu():
    bersihkan_isi()

    kotak = tk.Frame(frame_isi)
    kotak.place(relx=0.5, rely=0.47, anchor="center")

    tk.Label(kotak, text="===== SMART RETAIL =====",
             font=("Courier New", 20, "bold")).pack(pady=(0, 20))

    daftar_menu = [
        "1. Kelola Produk",
        "2. Transaksi Penjualan",
        "3. Cari Produk",
        "4. Laporan Penjualan",
        "5. Logout",
    ]
    nomor = 1
    for teks in daftar_menu:
        tk.Button(kotak, text=teks, font=("Arial", 11), width=32, pady=4,
                  command=lambda n=nomor: pilih_menu(n)).pack(pady=4)
        nomor = nomor + 1

    # fitur tambahan (bonus) taruh terpisah dari menu 1-5
    tk.Frame(kotak, height=1, bg=ABU).pack(fill="x", pady=(14, 8))
    tk.Button(kotak, text="Member Pelanggan", font=("Arial", 11),
              width=32, pady=4, command=halaman_member).pack()


def pilih_menu(nomor):
    if nomor == 1:
        halaman_produk()
    elif nomor == 2:
        halaman_transaksi()
    elif nomor == 3:
        halaman_cari()
    elif nomor == 4:
        if role_login == "admin":
            halaman_laporan()
        else:
            messagebox.showwarning("Akses Ditolak",
                                   "Laporan Penjualan hanya bisa dibuka oleh Admin.")
    elif nomor == 5:
        logout()


def refresh_semua():
    refresh_tabel_produk()
    refresh_tabel_cari()
    refresh_tabel_kasir()
    refresh_keranjang()
    refresh_tabel_member()
    refresh_member_aktif()
    refresh_riwayat()
    refresh_laporan()


def isi_tabel_produk(tree, keyword, dengan_modal=False):
    kosongkan_tabel(tree)
    daftar = ambil_produk(keyword)
    for p in daftar:
        if p["stok"] < BATAS_STOK_MENIPIS:
            tag = ("menipis",)
        else:
            tag = ()

        if dengan_modal:
            nilai = (p["id"], p["nama_produk"], rupiah(p["harga_modal"]),
                     rupiah(p["harga_jual"]), p["stok"])
        else:
            nilai = (p["id"], p["nama_produk"], rupiah(p["harga_jual"]), p["stok"])
        tambah_baris(tree, nilai, iid=p["id"], tags=tag)
    return len(daftar)


def halaman_produk():
    global var_cari_produk, tree_produk, lbl_jumlah_produk

    bersihkan_isi()
    admin = role_login == "admin"

    if admin:
        bar_atas("1. Kelola Produk")
    else:
        bar_atas("1. Daftar Produk")

    atas = tk.Frame(frame_isi)
    atas.pack(fill="x", padx=12, pady=5)
    tk.Label(atas, text="Cari Produk (nama / ID) :", font=FONT_BOLD).pack(side="left")
    var_cari_produk = tk.StringVar()
    var_cari_produk.trace_add("write", lambda *a: refresh_tabel_produk())
    tk.Entry(atas, textvariable=var_cari_produk, font=("Arial", 11),
             width=32).pack(side="left", padx=10)
    lbl_jumlah_produk = tk.Label(atas, font=FONT, fg=ABU)
    lbl_jumlah_produk.pack(side="right")

    if admin:
        kolom = [
            ("id", "ID", 60, "center"),
            ("nama", "Nama Barang", 320, "w"),
            ("modal", "Harga Modal", 130, "e"),
            ("jual", "Harga Jual", 130, "e"),
            ("stok", "Stok", 80, "center"),
        ]
    else:
        kolom = [
            ("id", "ID", 60, "center"),
            ("nama", "Nama Barang", 380, "w"),
            ("jual", "Harga Jual", 150, "e"),
            ("stok", "Stok", 80, "center"),
        ]

    frame, tree_produk = buat_tabel(frame_isi, kolom, tinggi=18)
    frame.pack(fill="both", expand=True, padx=12, pady=5)

    if admin:
        bawah = tk.Frame(frame_isi)
        bawah.pack(fill="x", padx=12, pady=10)
        buat_tombol(bawah, "Tambah Produk", form_tambah_produk, HIJAU).pack(
            side="left", padx=(0, 8))
        buat_tombol(bawah, "Update Produk", form_ubah_produk, PINK).pack(
            side="left", padx=8)
        buat_tombol(bawah, "Hapus Produk", proses_hapus_produk, MERAH).pack(
            side="left", padx=8)

    refresh_tabel_produk()


def refresh_tabel_produk():
    if not ada(tree_produk):
        return
    jumlah = isi_tabel_produk(tree_produk, var_cari_produk.get(),
                              role_login == "admin")
    lbl_jumlah_produk.config(text=str(jumlah) + " produk")


def form_tambah_produk():
    form_produk("Tambah Produk")


def form_ubah_produk():
    produk = produk_terpilih()
    if produk is not None:
        form_produk("Update Produk", produk)


def produk_terpilih():
    pilih = tree_produk.selection()
    if not pilih:
        messagebox.showwarning("Peringatan", "Pilih produk di tabel dulu!")
        return None
    return query_one("SELECT * FROM produk WHERE id = ?", (int(pilih[0]),))


def form_produk(judul, data=None):
    win = buat_dialog(judul)
    frm = tk.Frame(win, padx=25, pady=20)
    frm.pack()

    tk.Label(frm, text=judul, font=FONT_JUDUL).grid(
        row=0, column=0, columnspan=2, pady=(0, 12))

    nama_label = ["Nama Barang", "Harga Modal", "Harga Jual", "Stok"]
    kolom_isi = []
    for i in range(4):
        tk.Label(frm, text=nama_label[i] + " :", font=FONT).grid(
            row=i + 1, column=0, sticky="w", pady=5, padx=(0, 15))
        e = tk.Entry(frm, font=FONT, width=28)
        e.grid(row=i + 1, column=1, pady=5)
        kolom_isi.append(e)

    ent_nama, ent_modal, ent_jual, ent_stok = kolom_isi

    if data is not None:
        ent_nama.insert(0, data["nama_produk"])
        ent_modal.insert(0, data["harga_modal"])
        ent_jual.insert(0, data["harga_jual"])
        ent_stok.insert(0, data["stok"])

    buat_tombol(frm, "SIMPAN", lambda: simpan_form_produk(win, data, kolom_isi),
                HIJAU).grid(row=5, column=0, columnspan=2, sticky="ew", pady=(15, 0))
    ent_nama.focus()
    aktifkan_dialog(win)


def simpan_form_produk(win, data, kolom_isi):
    nama = kolom_isi[0].get().strip()
    if nama == "":
        messagebox.showerror("Error", "Nama barang wajib diisi!", parent=win)
        return

    try:
        modal = int(kolom_isi[1].get())
        jual = int(kolom_isi[2].get())
        stok = int(kolom_isi[3].get())
    except ValueError:
        messagebox.showerror("Error", "Harga modal, harga jual, dan stok harus angka!",
                             parent=win)
        return

    if modal < 0 or jual < 0 or stok < 0:
        messagebox.showerror("Error", "Angka tidak boleh negatif!", parent=win)
        return

    if data is None:
        tambah_produk(nama, modal, jual, stok)
    else:
        ubah_produk(data["id"], nama, modal, jual, stok)

    win.destroy()
    refresh_semua()
    messagebox.showinfo("Berhasil", "Data produk tersimpan.")


def proses_hapus_produk():
    produk = produk_terpilih()
    if produk is None:
        return

    jawab = messagebox.askyesno(
        "Konfirmasi",
        "Yakin menghapus produk?\n\n" + produk["nama_produk"] + "\n(Y/T)")
    if not jawab:
        return

    berhasil, pesan = hapus_produk(produk["id"])
    if berhasil:
        refresh_semua()
        messagebox.showinfo("Berhasil", pesan)
    else:
        messagebox.showerror("Gagal", pesan)


def halaman_cari():
    global var_cari_menu, tree_cari, lbl_jumlah_cari

    bersihkan_isi()
    bar_atas("3. Cari Produk")

    atas = tk.Frame(frame_isi)
    atas.pack(fill="x", padx=12, pady=5)
    tk.Label(atas, text="Cari Produk :", font=FONT_BOLD).pack(side="left")
    var_cari_menu = tk.StringVar()
    var_cari_menu.trace_add("write", lambda *a: refresh_tabel_cari())
    ent = tk.Entry(atas, textvariable=var_cari_menu, font=("Arial", 12), width=30)
    ent.pack(side="left", padx=10)
    ent.focus()
    lbl_jumlah_cari = tk.Label(atas, font=FONT, fg=ABU)
    lbl_jumlah_cari.pack(side="right")

    tk.Label(frame_isi, text="Ketik nama barang (contoh: gula) atau ID produk "
             "(contoh: 3), hasil muncul otomatis.",
             font=("Arial", 9), fg=ABU).pack(anchor="w", padx=12)

    kolom = [
        ("id", "ID", 60, "center"),
        ("nama", "Nama Barang", 380, "w"),
        ("jual", "Harga Jual", 150, "e"),
        ("stok", "Stok", 80, "center"),
    ]
    frame, tree_cari = buat_tabel(frame_isi, kolom, tinggi=18)
    frame.pack(fill="both", expand=True, padx=12, pady=8)

    refresh_tabel_cari()


def refresh_tabel_cari():
    if not ada(tree_cari):
        return
    jumlah = isi_tabel_produk(tree_cari, var_cari_menu.get())
    lbl_jumlah_cari.config(text=str(jumlah) + " produk")


def halaman_transaksi():
    global var_cari_kasir, tree_kasir, spin_jumlah, tree_keranjang
    global lbl_jumlah_item, var_member, lbl_member, lbl_subtotal
    global lbl_diskon_belanja, lbl_diskon_member, lbl_total, lbl_hint_diskon
    global var_bayar, lbl_kembalian

    bersihkan_isi()
    bar_atas("2. Transaksi Penjualan")

    isi = tk.Frame(frame_isi)
    isi.pack(fill="both", expand=True, padx=10, pady=5)
    isi.grid_rowconfigure(0, weight=1)
    isi.grid_columnconfigure(0, weight=4, uniform="kol")
    isi.grid_columnconfigure(1, weight=4, uniform="kol")
    isi.grid_columnconfigure(2, weight=3, uniform="kol")

    kiri = tk.LabelFrame(isi, text=" Daftar Produk ", font=FONT_BOLD)
    kiri.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
    tengah = tk.LabelFrame(isi, text=" Keranjang Belanja ", font=FONT_BOLD)
    tengah.grid(row=0, column=1, sticky="nsew", padx=5)
    kanan = tk.LabelFrame(isi, text=" Pembayaran ", font=FONT_BOLD)
    kanan.grid(row=0, column=2, sticky="nsew", padx=(5, 0))

    cari = tk.Frame(kiri)
    cari.pack(fill="x", padx=8, pady=(8, 0))
    tk.Label(cari, text="Cari :", font=FONT).pack(side="left")
    var_cari_kasir = tk.StringVar()
    var_cari_kasir.trace_add("write", lambda *a: refresh_tabel_kasir())
    tk.Entry(cari, textvariable=var_cari_kasir, font=FONT).pack(
        side="left", fill="x", expand=True, padx=(8, 0))

    frame, tree_kasir = buat_tabel(kiri, [
        ("id", "ID", 45, "center"),
        ("nama", "Produk", 175, "w"),
        ("harga", "Harga", 90, "e"),
        ("stok", "Stok", 55, "center"),
    ], tinggi=15)
    frame.pack(fill="both", expand=True, padx=8, pady=8)
    tree_kasir.bind("<Double-1>", lambda e: tambah_ke_keranjang())

    tambah = tk.Frame(kiri)
    tambah.pack(fill="x", padx=8, pady=(0, 10))
    tk.Label(tambah, text="Jumlah :", font=FONT).pack(side="left")
    spin_jumlah = tk.Spinbox(tambah, from_=1, to=9999, width=5, font=FONT)
    spin_jumlah.pack(side="left", padx=8)
    buat_tombol(tambah, "Tambah ke Keranjang", tambah_ke_keranjang).pack(side="left")

    frame2, tree_keranjang = buat_tabel(tengah, [
        ("id", "ID", 40, "center"),
        ("nama", "Produk", 140, "w"),
        ("jumlah", "Qty", 45, "center"),
        ("harga", "Harga", 85, "e"),
        ("subtotal", "Subtotal", 95, "e"),
    ], tinggi=15)
    frame2.pack(fill="both", expand=True, padx=8, pady=8)

    aksi = tk.Frame(tengah)
    aksi.pack(fill="x", padx=8, pady=(0, 10))
    buat_tombol(aksi, "Hapus Item", hapus_dari_keranjang, MERAH).pack(side="left")
    buat_tombol(aksi, "Kosongkan", kosongkan_keranjang).pack(side="left", padx=8)
    lbl_jumlah_item = tk.Label(aksi, font=FONT, fg=ABU)
    lbl_jumlah_item.pack(side="right")

    tk.Label(kanan, text="Member Pelanggan (kode / No. HP) :", font=FONT_BOLD).pack(
        anchor="w", padx=8, pady=(8, 2))

    baris_member = tk.Frame(kanan)
    baris_member.pack(fill="x", padx=8)
    var_member = tk.StringVar()
    ent_member = tk.Entry(baris_member, textvariable=var_member, font=FONT, width=14)
    ent_member.pack(side="left", fill="x", expand=True)
    ent_member.bind("<Return>", lambda e: pakai_member())
    buat_tombol(baris_member, "Pakai", pakai_member).pack(side="left", padx=(6, 0))

    lbl_member = tk.Label(kanan, text="Isi kode member / No. HP, lalu klik Pakai",
                          font=("Arial", 9), fg=ABU, anchor="w",
                          justify="left", wraplength=270)
    lbl_member.pack(fill="x", padx=8, pady=(6, 0))

    aksi_member = tk.Frame(kanan)
    aksi_member.pack(fill="x", padx=8, pady=(6, 0))
    buat_tombol(aksi_member, "Daftar Member Baru", form_daftar_member).pack(side="left")
    buat_tombol(aksi_member, "Lepas", lepas_member, MERAH).pack(side="left", padx=6)

    ringkas = tk.Frame(kanan, bd=1, relief="groove")
    ringkas.pack(fill="x", padx=8, pady=(12, 0))
    ringkas.grid_columnconfigure(1, weight=1)

    tk.Label(ringkas, text="Subtotal", font=FONT).grid(
        row=0, column=0, sticky="w", padx=8, pady=2)
    lbl_subtotal = tk.Label(ringkas, text="Rp0", font=FONT_BOLD)
    lbl_subtotal.grid(row=0, column=1, sticky="e", padx=8)

    tk.Label(ringkas, text="Diskon Belanja", font=FONT).grid(
        row=1, column=0, sticky="w", padx=8, pady=2)
    lbl_diskon_belanja = tk.Label(ringkas, text="-", font=FONT_BOLD)
    lbl_diskon_belanja.grid(row=1, column=1, sticky="e", padx=8)

    tk.Label(ringkas, text="Diskon Member", font=FONT).grid(
        row=2, column=0, sticky="w", padx=8, pady=2)
    lbl_diskon_member = tk.Label(ringkas, text="-", font=FONT_BOLD)
    lbl_diskon_member.grid(row=2, column=1, sticky="e", padx=8)

    lbl_total = tk.Label(kanan, text="Total Belanja : Rp0",
                         font=("Arial", 14, "bold"), fg=PINK)
    lbl_total.pack(pady=(12, 0))

    lbl_hint_diskon = tk.Label(kanan, text="", font=("Arial", 9), fg=HIJAU,
                               wraplength=270, justify="center")
    lbl_hint_diskon.pack()

    bayar = tk.Frame(kanan)
    bayar.pack(pady=(10, 4))
    tk.Label(bayar, text="Uang Bayar : Rp", font=("Arial", 11)).pack(side="left")
    var_bayar = tk.StringVar()
    var_bayar.trace_add("write", lambda *a: hitung_kembalian())
    tk.Entry(bayar, textvariable=var_bayar, font=("Arial", 12), width=12).pack(
        side="left", padx=4)

    lbl_kembalian = tk.Label(kanan, text="Kembalian : Rp0",
                             font=("Arial", 12, "bold"), fg=HIJAU)
    lbl_kembalian.pack(pady=4)

    buat_tombol(kanan, "BAYAR & CETAK STRUK", proses_bayar, HIJAU).pack(
        fill="x", padx=8, pady=(6, 10))

    refresh_tabel_kasir()
    refresh_keranjang()
    refresh_member_aktif()


def refresh_tabel_kasir():
    if not ada(tree_kasir):
        return
    kosongkan_tabel(tree_kasir)
    for p in ambil_produk(var_cari_kasir.get()):
        if p["stok"] < BATAS_STOK_MENIPIS:
            tag = ("menipis",)
        else:
            tag = ()
        tambah_baris(tree_kasir,
                     (p["id"], p["nama_produk"], rupiah(p["harga_jual"]), p["stok"]),
                     iid=p["id"], tags=tag)


def hitung_total():
    total = 0
    for id_produk, jumlah in keranjang.items():
        row = query_one("SELECT harga_jual FROM produk WHERE id = ?", (id_produk,))
        if row:
            total += row["harga_jual"] * jumlah
    return total


def member_aktif():
    global member_aktif_id
    if member_aktif_id is None:
        return None
    member = ambil_member_by_id(member_aktif_id)
    if member is None:
        member_aktif_id = None
    return member


def refresh_keranjang():
    if not ada(tree_keranjang):
        return
    kosongkan_tabel(tree_keranjang)

    subtotal = 0
    jumlah_pcs = 0
    for id_produk, jumlah in list(keranjang.items()):
        row = query_one("SELECT nama_produk, harga_jual FROM produk WHERE id = ?",
                        (id_produk,))
        if row is None:
            del keranjang[id_produk]
            continue
        sub = row["harga_jual"] * jumlah
        subtotal += sub
        jumlah_pcs += jumlah
        tambah_baris(tree_keranjang,
                     (id_produk, row["nama_produk"], jumlah,
                      rupiah(row["harga_jual"]), rupiah(sub)),
                     iid=id_produk)

    lbl_jumlah_item.config(
        text=str(len(keranjang)) + " jenis  |  " + str(jumlah_pcs) + " pcs")
    perbarui_ringkasan(subtotal)


def perbarui_ringkasan(subtotal=None):
    if not ada(lbl_total):
        return
    if subtotal is None:
        subtotal = hitung_total()
    h = hitung_diskon(subtotal, member_aktif())

    lbl_subtotal.config(text=rupiah(h["subtotal"]))

    if h["diskon_belanja"]:
        lbl_diskon_belanja.config(
            text="(" + str(h["persen_belanja"]) + "%)  -" + rupiah(h["diskon_belanja"]),
            fg=HIJAU)
    else:
        lbl_diskon_belanja.config(text="-", fg=ABU)

    if h["diskon_member"]:
        lbl_diskon_member.config(
            text="(" + str(h["persen_member"]) + "%)  -" + rupiah(h["diskon_member"]),
            fg=HIJAU)
    else:
        lbl_diskon_member.config(text="-", fg=ABU)

    lbl_total.config(text="Total Belanja : " + rupiah(h["total"]))

    if subtotal > 0:
        info = info_diskon_berikutnya(subtotal)
    else:
        info = None

    if info:
        kurang, persen = info
        lbl_hint_diskon.config(
            text="Belanja " + rupiah(kurang) + " lagi untuk diskon " + str(persen) + "%")
    elif subtotal > 0:
        lbl_hint_diskon.config(text="Diskon belanja tertinggi tercapai")
    else:
        lbl_hint_diskon.config(text="")

    hitung_kembalian()


def hitung_kembalian():
    if not ada(lbl_kembalian):
        return
    try:
        bayar = int(var_bayar.get())
    except ValueError:
        lbl_kembalian.config(text="Kembalian : Rp0", fg=HIJAU)
        return

    total = hitung_diskon(hitung_total(), member_aktif())["total"]
    if bayar >= total:
        lbl_kembalian.config(text="Kembalian : " + rupiah(bayar - total), fg=HIJAU)
    else:
        lbl_kembalian.config(text="Kurang : " + rupiah(total - bayar), fg=MERAH)


def tambah_ke_keranjang():
    pilih = tree_kasir.selection()
    if not pilih:
        messagebox.showwarning("Peringatan", "Pilih produk terlebih dahulu!")
        return

    try:
        jumlah = int(spin_jumlah.get())
    except ValueError:
        messagebox.showerror("Error", "Jumlah harus berupa angka!")
        return
    if jumlah <= 0:
        messagebox.showerror("Error", "Jumlah harus lebih dari 0!")
        return

    id_produk = int(pilih[0])
    produk = query_one("SELECT * FROM produk WHERE id = ?", (id_produk,))
    if produk is None:
        refresh_semua()
        return

    sudah_ada = keranjang.get(id_produk, 0)

    if sudah_ada + jumlah > produk["stok"]:
        messagebox.showerror(
            "ERROR",
            "ERROR:\nStok tidak mencukupi.\n\n"
            "Stok " + produk["nama_produk"] + " = " + str(produk["stok"]) +
            " (di keranjang: " + str(sudah_ada) + ")\n"
            "Silakan masukkan jumlah yang lebih kecil.")
        return

    keranjang[id_produk] = sudah_ada + jumlah
    refresh_keranjang()


def hapus_dari_keranjang():
    pilih = tree_keranjang.selection()
    if not pilih:
        messagebox.showwarning("Peringatan", "Pilih item di keranjang!")
        return
    keranjang.pop(int(pilih[0]), None)
    refresh_keranjang()


def kosongkan_keranjang():
    keranjang.clear()
    refresh_keranjang()


def pakai_member():
    global member_aktif_id
    kunci = var_member.get().strip()
    if kunci == "":
        messagebox.showwarning(
            "Member", "Masukkan kode member (contoh M0001) atau nomor HP!")
        return

    member = temukan_member(kunci)
    if member is None:
        messagebox.showerror(
            "Member",
            "Member tidak ditemukan.\n"
            "Periksa kode / nomor HP, atau daftarkan member baru.")
        return

    member_aktif_id = member["id"]
    var_member.set("")
    refresh_member_aktif()


def lepas_member():
    global member_aktif_id
    member_aktif_id = None
    refresh_member_aktif()


def pilih_member_baru(id_baru):
    global member_aktif_id
    member_aktif_id = id_baru
    refresh_member_aktif()


def form_daftar_member():
    form_member(callback=pilih_member_baru)


def refresh_member_aktif():
    if not ada(lbl_member):
        return
    member = member_aktif()
    if member is None:
        lbl_member.config(text="Isi kode member / No. HP, lalu klik Pakai", fg=ABU)
    else:
        level, persen = level_member(member["total_belanja"])
        lbl_member.config(
            text=member["nama"] + "  (" + member["kode"] + ")\n" +
                 "Level " + level + "  |  diskon member " + str(persen) + "%  |  " +
                 str(member["poin"]) + " poin",
            fg=HIJAU)
    perbarui_ringkasan()


def proses_bayar():
    global member_aktif_id

    if not keranjang:
        messagebox.showwarning("Keranjang Kosong", "Belum ada barang di keranjang!")
        return

    try:
        bayar = int(var_bayar.get())
    except ValueError:
        messagebox.showerror("Error", "Masukkan jumlah uang yang benar!")
        return

    try:
        hasil = simpan_transaksi(keranjang, bayar, user_login, member_aktif_id)
    except ValueError as err:
        messagebox.showerror("ERROR", str(err))
        refresh_semua()
        return

    teks = buat_struk(hasil)
    simpan_struk_txt(hasil, teks)

    keranjang.clear()
    member_aktif_id = None
    var_bayar.set("")
    refresh_semua()
    jendela_struk(teks)


def jendela_struk(teks):
    win = buat_dialog("Struk Belanja")

    tk.Label(win, text="Struk Belanja", font=FONT_JUDUL).pack(padx=20, pady=(15, 8))

    box = tk.Text(win, font=("Courier New", 11), width=34,
                  height=teks.count("\n") + 2, padx=8, pady=6)
    box.insert("1.0", teks)
    box.config(state="disabled")
    box.pack(padx=20)

    tk.Label(win, text="Struk tersimpan di folder: " + STRUK_DIR.name + "/",
             font=("Arial", 9), fg=ABU).pack(pady=(6, 0))
    buat_tombol(win, "Tutup", win.destroy).pack(pady=12)
    tengahkan(win)


def halaman_laporan():
    global lbl_jml_transaksi, lbl_pendapatan, lbl_total_diskon, lbl_jml_member
    global lbl_terlaris, lbl_terjual, list_menipis

    bersihkan_isi()
    bar_atas("4. Laporan Penjualan")

    ringkasan = tk.LabelFrame(frame_isi, text=" Ringkasan Penjualan ", font=FONT_BOLD,
                              padx=15, pady=10)
    ringkasan.pack(fill="x", padx=12, pady=8)
    ringkasan.grid_columnconfigure(1, weight=1)

    teks_label = ["Jumlah Transaksi :", "Total Penjualan :",
                  "Total Diskon Diberikan :", "Member Terdaftar :",
                  "Produk Terlaris :"]
    for i in range(len(teks_label)):
        tk.Label(ringkasan, text=teks_label[i], font=FONT).grid(
            row=i, column=0, sticky="w", pady=2)

    lbl_jml_transaksi = tk.Label(ringkasan, font=FONT_BOLD)
    lbl_jml_transaksi.grid(row=0, column=1, sticky="w", padx=15)
    lbl_pendapatan = tk.Label(ringkasan, font=FONT_BOLD)
    lbl_pendapatan.grid(row=1, column=1, sticky="w", padx=15)
    lbl_total_diskon = tk.Label(ringkasan, font=FONT_BOLD)
    lbl_total_diskon.grid(row=2, column=1, sticky="w", padx=15)
    lbl_jml_member = tk.Label(ringkasan, font=FONT_BOLD)
    lbl_jml_member.grid(row=3, column=1, sticky="w", padx=15)
    lbl_terlaris = tk.Label(ringkasan, font=FONT_BOLD)
    lbl_terlaris.grid(row=4, column=1, sticky="w", padx=15)
    lbl_terjual = tk.Label(ringkasan, font=FONT)
    lbl_terjual.grid(row=5, column=1, sticky="w", padx=15)

    tk.Label(frame_isi,
             text="Produk yang harus segera restock (stok kurang dari " +
                  str(BATAS_STOK_MENIPIS) + "):",
             font=FONT_BOLD, fg=MERAH).pack(anchor="w", padx=14, pady=(8, 2))

    kotak_list = tk.Frame(frame_isi)
    kotak_list.pack(fill="both", expand=True, padx=12, pady=(0, 8))
    list_menipis = tk.Listbox(kotak_list, font=("Arial", 11), height=8)
    scroll = ttk.Scrollbar(kotak_list, orient="vertical", command=list_menipis.yview)
    list_menipis.configure(yscrollcommand=scroll.set)
    scroll.pack(side="right", fill="y")
    list_menipis.pack(side="left", fill="both", expand=True)

    bawah = tk.Frame(frame_isi)
    bawah.pack(fill="x", padx=12, pady=(0, 12))
    buat_tombol(bawah, "Refresh", refresh_laporan).pack(side="left", padx=(0, 8))
    buat_tombol(bawah, "Riwayat Transaksi", jendela_riwayat, PINK).pack(
        side="left", padx=8)
    buat_tombol(bawah, "Export ke CSV", proses_export_csv, HIJAU).pack(
        side="left", padx=8)
    buat_tombol(bawah, "Grafik Penjualan", tampilkan_grafik).pack(side="left", padx=8)

    refresh_laporan()


def refresh_laporan():
    if not ada(list_menipis):
        return
    data = ambil_laporan()

    lbl_jml_transaksi.config(text=str(data["jumlah_transaksi"]))
    lbl_pendapatan.config(text=rupiah(data["pendapatan"]))
    lbl_total_diskon.config(text=rupiah(data["total_diskon"]))
    lbl_jml_member.config(text=str(data["jumlah_member"]))

    if data["terlaris"]:
        terjual = "{:,}".format(data["terlaris"]["terjual"]).replace(",", ".")
        lbl_terlaris.config(text=data["terlaris"]["nama_produk"])
        lbl_terjual.config(text="Terjual " + terjual + " pcs")
    else:
        lbl_terlaris.config(text="-  (belum ada transaksi)")
        lbl_terjual.config(text="")

    list_menipis.delete(0, "end")
    for p in data["menipis"]:
        list_menipis.insert("end", "- " + p["nama_produk"] + " (" + str(p["stok"]) + " pcs)")


def proses_export_csv():
    path = filedialog.asksaveasfilename(
        title="Simpan laporan CSV",
        defaultextension=".csv",
        initialfile="laporan_penjualan.csv",
        filetypes=[("CSV", "*.csv")])
    if not path:
        return

    try:
        jumlah = export_laporan_csv(path)
    except PermissionError:
        messagebox.showerror(
            "Gagal",
            "File tidak bisa ditulis. Tutup dulu file CSV yang sedang "
            "terbuka di Excel, lalu coba lagi.")
        return

    messagebox.showinfo("Export CSV",
                        "Berhasil mengekspor " + str(jumlah) + " baris ke:\n" + path)


def tampilkan_grafik():
    if not ADA_MATPLOTLIB:
        messagebox.showerror(
            "Error",
            "Matplotlib belum terinstall.\n\nInstall dengan:\npip install matplotlib")
        return

    rows = query_all(
        "SELECT substr(tanggal, 1, 10) AS hari, SUM(total_bayar) AS total "
        "FROM transaksi GROUP BY hari ORDER BY hari")
    if not rows:
        messagebox.showinfo("Grafik", "Belum ada data transaksi.")
        return

    hari = []
    total = []
    for r in rows:
        hari.append(r["hari"])
        total.append(r["total"])

    plt.figure(figsize=(9, 5))
    plt.bar(hari, total, color="hotpink")
    plt.title("Grafik Penjualan per Hari - Smart Retail")
    plt.xlabel("Tanggal")
    plt.ylabel("Total Penjualan (Rp)")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()


def jendela_riwayat():
    global win_riwayat, tree_riwayat

    if ada(win_riwayat):
        win_riwayat.lift()
        return

    win_riwayat = tk.Toplevel(window)
    win_riwayat.title("Riwayat Transaksi")
    win_riwayat.transient(window)

    tk.Label(win_riwayat, text="Riwayat Transaksi", font=FONT_JUDUL).pack(
        padx=12, pady=(12, 0), anchor="w")
    tk.Label(win_riwayat, text="Klik dua kali pada transaksi untuk melihat detail barang",
             font=("Arial", 9), fg=ABU).pack(padx=12, anchor="w")

    frame, tree_riwayat = buat_tabel(win_riwayat, [
        ("id", "ID", 50, "center"),
        ("tanggal", "Tanggal", 130, "center"),
        ("kasir", "Kasir", 80, "center"),
        ("total", "Total", 110, "e"),
        ("bayar", "Uang Diterima", 110, "e"),
        ("kembali", "Kembalian", 100, "e"),
        ("diskon", "Diskon", 100, "e"),
        ("member", "Member", 140, "w"),
    ], tinggi=18)
    frame.pack(fill="both", expand=True, padx=12, pady=10)
    tree_riwayat.bind("<Double-1>", lihat_detail_transaksi)

    buat_tombol(win_riwayat, "Tutup", win_riwayat.destroy).pack(pady=(0, 12))

    refresh_riwayat()
    tengahkan(win_riwayat)


def refresh_riwayat():
    if not ada(tree_riwayat):
        return
    kosongkan_tabel(tree_riwayat)
    for t in ambil_riwayat():
        diskon = t["diskon_belanja"] + t["diskon_member"]
        if diskon:
            teks_diskon = rupiah(diskon)
        else:
            teks_diskon = "-"
        tambah_baris(tree_riwayat,
                     (t["id"], format_tanggal(t["tanggal"]), t["kasir"],
                      rupiah(t["total_bayar"]), rupiah(t["uang_diterima"]),
                      rupiah(t["kembalian"]), teks_diskon,
                      t["nama_member"] or "-"),
                     iid=t["id"])


def lihat_detail_transaksi(event=None):
    pilih = tree_riwayat.selection()
    if not pilih:
        return
    id_transaksi = int(pilih[0])
    detail = ambil_detail_transaksi(id_transaksi)
    trx = ambil_transaksi(id_transaksi)

    win = buat_dialog("Detail Transaksi #" + str(id_transaksi))

    tk.Label(win, text="Detail Transaksi #" + str(id_transaksi),
             font=FONT_JUDUL).pack(padx=15, pady=(14, 8), anchor="w")

    tinggi = min(max(len(detail), 3), 12)
    frame, tree = buat_tabel(win, [
        ("nama", "Produk", 220, "w"),
        ("jumlah", "Qty", 60, "center"),
        ("harga", "Harga", 100, "e"),
        ("subtotal", "Subtotal", 110, "e"),
    ], tinggi=tinggi)
    frame.pack(padx=15, pady=(0, 8))

    for d in detail:
        tambah_baris(tree, (d["nama_produk"], d["jumlah"],
                            rupiah(d["harga"]), rupiah(d["subtotal"])))

    if trx is not None:
        baris = [("Subtotal", rupiah(trx["subtotal"]))]
        if trx["diskon_belanja"]:
            baris.append(("Diskon Belanja", "-" + rupiah(trx["diskon_belanja"])))
        if trx["diskon_member"]:
            baris.append(("Diskon Member", "-" + rupiah(trx["diskon_member"])))
        if trx["nama_member"]:
            baris.append(("Member", trx["nama_member"] + " (" + trx["kode_member"] + ")"))
            baris.append(("Poin Didapat", "+" + str(trx["poin_didapat"])))
        baris.append(("Total Bayar", rupiah(trx["total_bayar"])))

        ring = tk.Frame(win, bd=1, relief="groove")
        ring.pack(fill="x", padx=15, pady=(0, 4))
        ring.grid_columnconfigure(1, weight=1)
        for i in range(len(baris)):
            if i == len(baris) - 1:
                font_baris = FONT_BOLD
            else:
                font_baris = FONT
            tk.Label(ring, text=baris[i][0], font=font_baris).grid(
                row=i, column=0, sticky="w", padx=(10, 20), pady=2)
            tk.Label(ring, text=baris[i][1], font=FONT_BOLD).grid(
                row=i, column=1, sticky="e", padx=(0, 10), pady=2)

    buat_tombol(win, "Tutup", win.destroy).pack(pady=(8, 14))
    tengahkan(win)


def halaman_member():
    global var_cari_member, tree_member, lbl_jumlah_member

    bersihkan_isi()
    bar_atas("Member Pelanggan")
    admin = role_login == "admin"

    atas = tk.Frame(frame_isi)
    atas.pack(fill="x", padx=12, pady=5)
    tk.Label(atas, text="Cari Member (nama / kode / No. HP) :", font=FONT_BOLD).pack(
        side="left")
    var_cari_member = tk.StringVar()
    var_cari_member.trace_add("write", lambda *a: refresh_tabel_member())
    tk.Entry(atas, textvariable=var_cari_member, font=("Arial", 11),
             width=30).pack(side="left", padx=10)
    lbl_jumlah_member = tk.Label(atas, font=FONT, fg=ABU)
    lbl_jumlah_member.pack(side="right")

    frame, tree_member = buat_tabel(frame_isi, [
        ("kode", "Kode", 80, "center"),
        ("nama", "Nama Member", 230, "w"),
        ("telepon", "No. HP", 140, "center"),
        ("level", "Level", 100, "center"),
        ("poin", "Poin", 80, "center"),
        ("belanja", "Total Belanja", 140, "e"),
        ("daftar", "Terdaftar", 110, "center"),
    ], tinggi=12)
    frame.pack(fill="both", expand=True, padx=12, pady=5)

    bawah = tk.Frame(frame_isi)
    bawah.pack(fill="x", padx=12, pady=6)
    buat_tombol(bawah, "Daftar Member", form_tambah_member, HIJAU).pack(
        side="left", padx=(0, 8))
    if admin:
        buat_tombol(bawah, "Update Member", form_ubah_member, PINK).pack(
            side="left", padx=8)
        buat_tombol(bawah, "Hapus Member", proses_hapus_member, MERAH).pack(
            side="left", padx=8)

    aturan = tk.LabelFrame(frame_isi, text=" Ketentuan Diskon & Member ", font=FONT_BOLD)
    aturan.pack(fill="x", padx=12, pady=(4, 12))
    tk.Label(aturan, text=teks_aturan(), font=FONT, justify="left",
             anchor="w").pack(fill="x", padx=10, pady=8)

    refresh_tabel_member()


def refresh_tabel_member():
    if not ada(tree_member):
        return
    kosongkan_tabel(tree_member)
    daftar = cari_member(var_cari_member.get())
    for m in daftar:
        level, _ = level_member(m["total_belanja"])
        tambah_baris(tree_member,
                     (m["kode"], m["nama"], m["telepon"], level, m["poin"],
                      rupiah(m["total_belanja"]),
                      format_tanggal_pendek(m["tanggal_daftar"])),
                     iid=m["id"])
    lbl_jumlah_member.config(text=str(len(daftar)) + " member")


def member_terpilih():
    pilih = tree_member.selection()
    if not pilih:
        messagebox.showwarning("Peringatan", "Pilih member di tabel dulu!")
        return None
    return ambil_member_by_id(int(pilih[0]))


def form_tambah_member():
    form_member()


def form_ubah_member():
    member = member_terpilih()
    if member is not None:
        form_member(data=member)


def proses_hapus_member():
    global member_aktif_id

    member = member_terpilih()
    if member is None:
        return

    jawab = messagebox.askyesno(
        "Konfirmasi",
        "Yakin menghapus member?\n\n" + member["nama"] + " (" + member["kode"] + ")\n(Y/T)")
    if not jawab:
        return

    berhasil, pesan = hapus_member(member["id"])
    if berhasil:
        if member_aktif_id == member["id"]:
            member_aktif_id = None
        refresh_semua()
        messagebox.showinfo("Berhasil", pesan)
    else:
        messagebox.showerror("Gagal", pesan)


def form_member(data=None, callback=None):
    if data is None:
        judul = "Daftar Member Baru"
    else:
        judul = "Update Member"

    win = buat_dialog(judul)
    frm = tk.Frame(win, padx=25, pady=20)
    frm.pack()

    tk.Label(frm, text=judul, font=FONT_JUDUL).grid(
        row=0, column=0, columnspan=2, pady=(0, 12))

    tk.Label(frm, text="Nama Lengkap :", font=FONT).grid(
        row=1, column=0, sticky="w", pady=5, padx=(0, 15))
    ent_nama = tk.Entry(frm, font=FONT, width=28)
    ent_nama.grid(row=1, column=1, pady=5)

    tk.Label(frm, text="No. HP :", font=FONT).grid(
        row=2, column=0, sticky="w", pady=5, padx=(0, 15))
    ent_hp = tk.Entry(frm, font=FONT, width=28)
    ent_hp.grid(row=2, column=1, pady=5)

    if data is not None:
        ent_nama.insert(0, data["nama"])
        ent_hp.insert(0, data["telepon"])

    buat_tombol(frm, "SIMPAN",
                lambda: simpan_form_member(win, data, callback, ent_nama, ent_hp),
                HIJAU).grid(row=3, column=0, columnspan=2, sticky="ew", pady=(15, 0))
    ent_nama.focus()
    aktifkan_dialog(win)


def simpan_form_member(win, data, callback, ent_nama, ent_hp):
    nama = ent_nama.get().strip()
    telepon = normalisasi_telepon(ent_hp.get().strip())

    if nama == "":
        messagebox.showerror("Error", "Nama member wajib diisi!", parent=win)
        return
    if not telepon.isdigit() or not 9 <= len(telepon) <= 15:
        messagebox.showerror("Error", "No. HP harus berupa angka (9 - 15 digit)!",
                             parent=win)
        return

    id_baru = None
    try:
        if data is None:
            id_baru = tambah_member(nama, telepon)
        else:
            ubah_member(data["id"], nama, telepon)
    except ValueError as err:
        messagebox.showerror("Error", str(err), parent=win)
        return

    win.destroy()
    refresh_semua()

    if data is None:
        member = ambil_member_by_id(id_baru)
        if callback:
            callback(id_baru)
        messagebox.showinfo(
            "Berhasil", "Member berhasil didaftarkan.\nKode member: " + member["kode"])
    else:
        messagebox.showinfo("Berhasil", "Data member tersimpan.")


def main():
    global window

    init_db()

    window = tk.Tk()
    window.title("Smart Retail - Sistem Kasir")

    lebar = 1200
    tinggi = min(720, max(window.winfo_screenheight() - 80, 600))
    x = max((window.winfo_screenwidth() - lebar) // 2, 0)
    y = max((window.winfo_screenheight() - tinggi) // 2 - 20, 0)
    window.geometry(str(lebar) + "x" + str(tinggi) + "+" + str(x) + "+" + str(y))
    window.minsize(1100, 600)

    window.configure(bg=PINK_MUDA)
    window.option_add("*Frame.Background", PINK_MUDA)
    window.option_add("*Label.Background", PINK_MUDA)
    window.option_add("*Labelframe.Background", PINK_MUDA)
    window.option_add("*Checkbutton.Background", PINK_MUDA)
    window.option_add("*Checkbutton.activeBackground", PINK_MUDA)
    window.option_add("*Toplevel.Background", PINK_MUDA)
    window.option_add("*Button.Background", PINK_SEDANG)
    window.option_add("*Button.activeBackground", PINK)

    style = ttk.Style()
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass
    style.configure("Treeview", rowheight=24, font=FONT)
    style.configure("Treeview.Heading", font=FONT_BOLD, background=PINK,
                    foreground=PUTIH)
    style.map("Treeview", background=[("selected", PINK)],
              foreground=[("selected", PUTIH)])
    style.map("Treeview.Heading", background=[("active", PINK)])

    tampilkan_login()
    window.mainloop()


if __name__ == "__main__":
    main()
