"""
extract_iso.py
==============

Script Python untuk membaca struktur file ISO PlayStation (PS1/PS2) dan
mengekstrak isinya menggunakan library pycdlib.

PlayStation discs umumnya menggunakan format ISO 9660 (Level 1 atau Level 2)
dengan ekstensi Rock Ridge atau sistem file khusus. pycdlib mendukung
pembacaan sistem file ISO 9660 standar.

Persyaratan:
    pip install pycdlib

Penggunaan:
    python extract_iso.py <file.iso> [output_dir]

Jika output_dir tidak ditentukan, file diekstrak ke folder dengan nama
sama sebagai file ISO (tanpa ekstensi).
"""

import os
import sys
import pycdlib


def iso_to_host_path(iso_path: str) -> str:
    """
    Mengonversi path dari format ISO 9660 (yang digunakan pycdlib)
    menjadi path filesystem yang valid di host.

    pycdlib mengembalikan path dengan format seperti:
        /DIRECTORY/FILE.EXT;1

    Fungsi ini menghapus nomor versi (;1) dan mengonversi
    pemisah path menjadi yang sesuai dengan OS host.
    """
    # Hapus nomor versi (semicolon dan angka di akhir)
    if ";" in iso_path:
        iso_path = iso_path.split(";")[0]

    # Hapus leading slash
    iso_path = iso_path.lstrip("/")

    # Ganti pemisah path ISO dengan os.sep
    host_path = iso_path.replace("/", os.sep)

    return host_path


def list_iso_contents(iso: pycdlib.PyCdlib, iso_dir: str = "/") -> list:
    """
    Rekursif mencatat semua file dan direktori dalam ISO.

    Returns list of dict dengan kunci:
        - iso_path: path dalam format ISO 9660
        - host_path: path yang siap ditulis ke filesystem host
        - is_directory: boolean
        - size: ukuran file dalam bytes (0 untuk direktori)
    """
    entries = []

    try:
        children = iso.list_children(iso_path=iso_dir)
    except Exception as e:
        print(f"[!] Tidak dapat membaca direktori {iso_dir}: {e}")
        return entries

    for child in children:
        # pycdlib mengembalikan record dengan atribut seperti:
        #   child.file_identifier(), child.is_directory(), child.file_size()
        file_id = child.file_identifier().decode("utf-8", errors="replace")
        # file_identifier bisa berupa "." atau ".." untuk self/parent dir
        if file_id in (".", ".."):
            continue

        child_iso_path = iso_dir.rstrip("/") + "/" + file_id
        is_dir = child.is_directory()
        size = child.file_size() if not is_dir else 0

        entries.append({
            "iso_path": child_iso_path,
            "host_path": iso_to_host_path(child_iso_path),
            "is_directory": is_dir,
            "size": size,
        })

        if is_dir:
            entries.extend(list_iso_contents(iso, child_iso_path))

    return entries


def extract_iso(iso_file: str, output_dir: str = None) -> None:
    """
    Mengekstrak semua isi ISO PlayStation ke output_dir.
    """
    if not os.path.isfile(iso_file):
        print(f"[!] File ISO tidak ditemukan: {iso_file}")
        sys.exit(1)

    if output_dir is None:
        base = os.path.splitext(os.path.basename(iso_file))[0]
        output_dir = os.path.join(os.getcwd(), base)

    os.makedirs(output_dir, exist_ok=True)
    print(f"[*] Membuka ISO: {iso_file}")
    print(f"[*] Output directory: {output_dir}")

    iso = pycdlib.PyCdlib()
    try:
        iso.open(iso_file)

        # Tampilkan informasi volume
        try:
            vol_id = iso.get_volume_identifier().decode("utf-8", errors="replace").strip()
            print(f"[*] Volume ID: {vol_id}")
        except Exception:
            print("[*] Volume ID: (tidak dapat dibaca)")

        # Daftar semua entri
        print("[*] Memindai struktur file ISO...")
        entries = list_iso_contents(iso)

        files = [e for e in entries if not e["is_directory"]]
        dirs = [e for e in entries if e["is_directory"]]

        print(f"[*] Ditemukan {len(dirs)} direktori dan {len(files)} file")

        # Buat semua direktori
        for d in dirs:
            full_path = os.path.join(output_dir, d["host_path"])
            os.makedirs(full_path, exist_ok=True)

        # Ekstrak semua file
        for f in files:
            out_path = os.path.join(output_dir, f["host_path"])
            os.makedirs(os.path.dirname(out_path), exist_ok=True)

            try:
                iso.extract_from_path(out_path, iso_path=f["iso_path"])
                print(f"    [OK] {f['host_path']} ({f['size']} bytes)")
            except Exception as e:
                print(f"    [ERR] {f['host_path']}: {e}")

        print(f"\n[+] Ekstraksi selesai. File disimpan di: {output_dir}")

    finally:
        iso.close()


def main():
    if len(sys.argv) < 2:
        print("Penggunaan: python extract_iso.py <file.iso> [output_dir]")
        print()
        print("Contoh:")
        print("  python extract_iso.py game.iso")
        print("  python extract_iso.py game.iso ./ekstraksi")
        sys.exit(1)

    iso_file = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None

    extract_iso(iso_file, output_dir)


if __name__ == "__main__":
    main()