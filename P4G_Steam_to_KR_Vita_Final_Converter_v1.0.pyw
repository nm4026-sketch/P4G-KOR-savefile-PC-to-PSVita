#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Persona 4 Golden
Steam -> Korean PS Vita (PCSH00021)
Final Converter v1.0

Confirmed conversion rule from real-file testing:
- Operate only on an EXISTING SLOTn created directly by vita-savemgr.
- Keep Korean player-name buffer #1: KR 0x0010..0x0023
- Keep Korean structural value at KR 0x0044
- Keep Korean player-name buffer #2: KR 0x0054..0x0067
- Transplant all other mapped pre-Rescue data from Steam.
- Keep KR 0x15100 onward (Rescue / Retry / tail) byte-for-byte.
- Keep sdslot.dat and system.bin unchanged.
- Do NOT recalculate the trailing Korean checksum byte.
- Make a ZIP backup of the entire selected savemgr SLOT before modification.

Observed working in user testing:
- Save loads without C2-12828-1
- Money inheritance confirmed
- Social Stats inheritance confirmed
"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import struct
import traceback
import zipfile
from datetime import datetime
from pathlib import Path

TITLE_ID = "PCSH00021"
STEAM_APP_ID = "1113000"

KR_SIZE = 0x30000
SDSLOT_SIZE = 0x40400

PC_RESCUE = 0x15120
KR_RESCUE = 0x15100
KR_CHECK_BYTE = 0x2FC34

MAX_GAME_SLOT = 16


class ConverterError(RuntimeError):
    pass


def pair(data: bytes, off: int) -> tuple[int, int]:
    return struct.unpack_from("<II", data, off)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def validate_steam_data(data: bytes, label: str) -> None:
    if len(data) < 0x15128:
        raise ConverterError(
            f"{label}: Steam P4G 세이브로 보기에는 파일이 너무 작습니다."
        )

    if pair(data, PC_RESCUE) != (0x0F, 0x3FA4):
        raise ConverterError(
            f"{label}: 지원하는 Steam P4G 세이브 구조가 아닙니다.\n"
            f"0x15120 = {pair(data, PC_RESCUE)}"
        )


def validate_korean_data(data: bytes, label: str) -> None:
    if len(data) != KR_SIZE:
        raise ConverterError(
            f"{label}: 한국판 PCSH00021 data 파일 크기가 0x30000이 아닙니다.\n"
            f"실제 크기: 0x{len(data):X}"
        )

    checks = (
        (0x15100, (0x0F, 0x1EF0), "Rescue"),
        (0x16FF8, (0x10, 0x80), "post-Rescue"),
        (0x17C0C, (0x10000001, 0x04), "Retry1"),
        (0x17C18, (0x10000002, 0x04), "Retry2"),
        (0x17C24, (0x10000003, 0x18000), "Retry3"),
        (0x2FC2C, (0x2000, 0x01), "Checksum record"),
    )

    for off, expected, name in checks:
        got = pair(data, off)
        if got != expected:
            raise ConverterError(
                f"{label}: 한국판 {name} 구조 검증 실패 @0x{off:X}\n"
                f"expected={expected}, got={got}"
            )


def verify_binslot_pair(data_path: Path, binslot_path: Path) -> None:
    data = data_path.read_bytes()
    bs = binslot_path.read_bytes()

    if len(bs) < 0x28 or bs[:8] != b"SAVE0001":
        raise ConverterError(
            f"{binslot_path.name}: 올바른 Steam P4G .binslot 파일이 아닙니다."
        )

    slotdata = bs[0x28:]

    expected_slot_md5 = hashlib.md5(slotdata + b"P4GOLDEN").digest()
    expected_data_md5 = hashlib.md5(data).digest()

    if bs[0x08:0x18] != expected_slot_md5:
        raise ConverterError(
            f"{binslot_path.name}: SlotData MD5 검증 실패"
        )

    if bs[0x18:0x28] != expected_data_md5:
        raise ConverterError(
            f"{binslot_path.name}: data 파일 MD5 검증 실패"
        )


def parse_binslot_metadata(path: Path) -> dict[str, str]:
    raw = path.read_bytes()
    text = raw[0x28:0x28 + 0x188].decode("utf-8", errors="replace")

    def grab(pattern: str, default: str = "") -> str:
        m = re.search(pattern, text, re.MULTILINE)
        return m.group(1).strip() if m else default

    return {
        "name": grab(r"^Name:([^\r\n]+)"),
        "date": grab(r"^Date:([^\r\n]+)"),
        "location": grab(r"^Location:([^\r\n]+)"),
        "difficulty": grab(r"^Difficulty:([^\r\n]+)"),
        "play_time": grab(r"^Play Time:([^\r\n]+)"),
        "times_cleared": grab(r"^Times Cleared:([^\r\n]+)", "0"),
        "ending": grab(r"^([^\r\n]*Ending[^\r\n]*Cleared)"),
    }


def discover_steam_slots(remote: Path) -> list[int]:
    slots = []
    for n in range(1, MAX_GAME_SLOT + 1):
        d = remote / f"data00{n:02}.bin"
        b = remote / f"data00{n:02}.binslot"
        if d.is_file() and b.is_file():
            try:
                verify_binslot_pair(d, b)
                validate_steam_data(d.read_bytes(), d.name)
                slots.append(n)
            except Exception:
                continue
    return slots


def discover_vita_game_slots(slot_dir: Path) -> list[int]:
    sd_path = slot_dir / "sce_sys" / "sdslot.dat"
    if not sd_path.is_file():
        return []

    sd = sd_path.read_bytes()
    if len(sd) != SDSLOT_SIZE or sd[:4] != b"SDSL":
        return []

    slots = []
    for n in range(1, MAX_GAME_SLOT + 1):
        p = slot_dir / f"data00{n:02}.bin"
        if not p.is_file():
            continue

        try:
            validate_korean_data(p.read_bytes(), p.name)
        except Exception:
            continue

        flag_off = 0x200 + n
        record_off = 0x400 + n * 0x400

        if (
            flag_off < len(sd)
            and sd[flag_off] == 1
            and any(sd[record_off:record_off + 0x400])
        ):
            slots.append(n)

    return slots


def validate_existing_savemgr_slot(path: Path) -> Path:
    path = path.expanduser().resolve()

    if not path.is_dir():
        raise ConverterError("선택한 vita-savemgr SLOT 폴더가 존재하지 않습니다.")

    if not re.fullmatch(r"SLOT\d+", path.name, re.IGNORECASE):
        raise ConverterError(
            "반드시 vita-savemgr가 직접 만든 기존 SLOTn 폴더를 선택하세요.\n"
            r"예: ...\data\savegames\PCSH00021\SLOT0"
        )

    if path.parent.name.upper() != TITLE_ID:
        raise ConverterError(
            f"선택한 SLOT의 상위 폴더가 {TITLE_ID}가 아닙니다."
        )

    sdslot = path / "sce_sys" / "sdslot.dat"
    if not sdslot.is_file():
        raise ConverterError("선택한 SLOT에 sce_sys\\sdslot.dat가 없습니다.")

    sd = sdslot.read_bytes()
    if len(sd) != SDSLOT_SIZE or sd[:4] != b"SDSL":
        raise ConverterError(
            "sdslot.dat가 정상적인 PCSH00021 vita-savemgr 백업 구조가 아닙니다."
        )

    return path


def pc_source_offset_for_kr(kr_off: int) -> int:
    """
    Confirmed PC -> Korean mapping before Rescue.

    KR 0x0000..0x000F -> PC same
    KR 0x0024..0x0053 -> PC +0x10
    KR 0x0068..0x150FF -> PC +0x20

    Korean name buffers:
      0x0010..0x0023
      0x0054..0x0067
    are never copied.

    KR 0x0044 is also never copied.
    """

    if 0x0000 <= kr_off < 0x0010:
        return kr_off

    if 0x0024 <= kr_off < 0x0054:
        return kr_off + 0x10

    if 0x0068 <= kr_off < 0x15100:
        return kr_off + 0x20

    raise ConverterError(
        f"내부 매핑 오류: Korean offset 0x{kr_off:X}"
    )


def copy_mapped_range(
    out: bytearray,
    pc: bytes,
    start: int,
    end: int,
) -> None:

    pos = start

    while pos < end:
        if 0x0000 <= pos < 0x0010:
            boundary = min(end, 0x0010)

        elif 0x0024 <= pos < 0x0054:
            boundary = min(end, 0x0054)

        elif 0x0068 <= pos < 0x15100:
            boundary = end

        else:
            raise ConverterError(
                f"내부 매핑 오류: range includes 0x{pos:X}"
            )

        pc_start = pc_source_offset_for_kr(pos)
        size = boundary - pos

        out[pos:boundary] = pc[pc_start:pc_start + size]
        pos = boundary


def convert_data(pc: bytes, kr: bytes) -> bytes:
    """
    Final confirmed conversion rule:
      - preserve Korean names
      - preserve KR 0x44
      - transplant all other mapped pre-Rescue bytes
      - preserve all KR Rescue/Retry/tail bytes
      - preserve trailing checksum byte exactly as-is
    """

    validate_steam_data(pc, "Steam source")
    validate_korean_data(kr, "Korean target")

    out = bytearray(kr)

    ranges = (
        (0x0000, 0x0010),
        (0x0024, 0x0044),
        # 0x0044 intentionally preserved
        (0x0045, 0x0054),
        # 0x0054..0x0067 Korean name #2 preserved
        (0x0068, 0x15100),
    )

    for start, end in ranges:
        copy_mapped_range(out, pc, start, end)

    # Hard invariants.
    if out[0x44] != kr[0x44]:
        raise ConverterError("안전 검증 실패: KR 0x44가 변경되었습니다.")

    if out[0x10:0x24] != kr[0x10:0x24]:
        raise ConverterError("안전 검증 실패: 한국판 이름 버퍼 #1 변경")

    if out[0x54:0x68] != kr[0x54:0x68]:
        raise ConverterError("안전 검증 실패: 한국판 이름 버퍼 #2 변경")

    # Rescue / Retry / tail must remain byte-identical.
    if out[KR_RESCUE:] != kr[KR_RESCUE:]:
        raise ConverterError(
            "안전 검증 실패: 한국판 Rescue/Retry 이후 영역이 변경되었습니다."
        )

    # Explicitly preserve checksum byte as part of the tail.
    if out[KR_CHECK_BYTE] != kr[KR_CHECK_BYTE]:
        raise ConverterError("안전 검증 실패: checksum byte가 변경되었습니다.")

    result = bytes(out)
    validate_korean_data(result, "Converted Korean data")

    return result


def backup_root() -> Path:
    root = Path.home() / "Documents" / "P4G_Vita_Backups"
    root.mkdir(parents=True, exist_ok=True)
    return root


def create_zip_backup(slot_dir: Path, note: str) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_path = backup_root() / f"{TITLE_ID}_{slot_dir.name}_{stamp}.zip"

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        manifest = [
            f"title_id={TITLE_ID}",
            f"source_slot={slot_dir}",
            f"created={datetime.now().isoformat(timespec='seconds')}",
            f"note={note}",
            "",
            "SHA256:",
        ]

        for p in sorted(x for x in slot_dir.rglob("*") if x.is_file()):
            rel = p.relative_to(slot_dir).as_posix()
            z.write(p, rel)
            manifest.append(f"{sha256_file(p)}  {rel}")

        z.writestr(
            "CONVERTER_BACKUP_MANIFEST.txt",
            "\n".join(manifest) + "\n",
        )

    return zip_path


def atomic_write(path: Path, data: bytes) -> None:
    tmp = path.with_name(path.name + ".converter_tmp")

    with open(tmp, "wb") as f:
        f.write(data)
        f.flush()

        try:
            os.fsync(f.fileno())
        except OSError:
            pass

    os.replace(tmp, path)


def restore_backup_zip(zip_path: Path, slot_dir: Path) -> None:
    zip_path = zip_path.expanduser().resolve()
    slot_dir = validate_existing_savemgr_slot(slot_dir)

    if not zip_path.is_file():
        raise ConverterError("선택한 ZIP 백업 파일이 없습니다.")

    # Back up current state before restoring an older backup.
    create_zip_backup(
        slot_dir,
        note="automatic safety backup before ZIP restore",
    )

    with zipfile.ZipFile(zip_path, "r") as z:
        members = [
            i for i in z.infolist()
            if not i.is_dir()
            and i.filename != "CONVERTER_BACKUP_MANIFEST.txt"
            and i.filename != "PATCH_BACKUP_MANIFEST.txt"
        ]

        for info in members:
            rel = Path(info.filename)

            if rel.is_absolute() or ".." in rel.parts:
                raise ConverterError(
                    "ZIP 내부에 안전하지 않은 경로가 있습니다."
                )

        # Remove current files but keep the existing savemgr SLOT directory.
        for p in sorted(
            [x for x in slot_dir.rglob("*") if x.is_file()],
            reverse=True,
        ):
            p.unlink()

        for p in sorted(
            [x for x in slot_dir.rglob("*") if x.is_dir()],
            key=lambda x: len(x.parts),
            reverse=True,
        ):
            try:
                p.rmdir()
            except OSError:
                pass

        for info in members:
            target = slot_dir / info.filename
            target.parent.mkdir(parents=True, exist_ok=True)

            with z.open(info, "r") as src, open(target, "wb") as dst:
                shutil.copyfileobj(src, dst)

    validate_existing_savemgr_slot(slot_dir)


def find_steam_candidates() -> list[Path]:
    if os.name != "nt":
        return []

    roots = [
        Path(r"C:\Program Files (x86)\Steam"),
        Path(r"C:\Program Files\Steam"),
        Path(r"C:\Steam"),
    ]

    try:
        import winreg

        for key_path in (
            r"Software\Valve\Steam",
            r"Software\WOW6432Node\Valve\Steam",
        ):
            try:
                with winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    key_path,
                ) as key:
                    value, _ = winreg.QueryValueEx(key, "SteamPath")
                    roots.insert(0, Path(str(value)))
            except OSError:
                pass

    except Exception:
        pass

    found = []
    seen = set()

    for root in roots:
        userdata = root / "userdata"

        if not userdata.is_dir():
            continue

        try:
            users = list(userdata.iterdir())
        except OSError:
            continue

        for user in users:
            remote = user / STEAM_APP_ID / "remote"

            if not remote.is_dir():
                continue

            if not discover_steam_slots(remote):
                continue

            key = str(remote.resolve()).lower()

            if key not in seen:
                seen.add(key)
                found.append(remote)

    found.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return found


def find_vita_candidates() -> list[Path]:
    if os.name != "nt":
        return []

    found = []
    seen = set()

    for letter in range(ord("C"), ord("Z") + 1):
        drive = Path(chr(letter) + ":\\")

        if not drive.exists():
            continue

        candidate_title_dirs = (
            drive / "data" / "savegames" / TITLE_ID,
            drive / "ux0" / "data" / "savegames" / TITLE_ID,
        )

        for title in candidate_title_dirs:
            if not title.is_dir():
                continue

            try:
                children = list(title.iterdir())
            except OSError:
                continue

            for p in children:
                if not p.is_dir():
                    continue

                if not re.fullmatch(r"SLOT\d+", p.name, re.IGNORECASE):
                    continue

                try:
                    validate_existing_savemgr_slot(p)
                except Exception:
                    continue

                key = str(p.resolve()).lower()

                if key not in seen:
                    seen.add(key)
                    found.append(p)

    found.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return found


def run_gui() -> None:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    root = tk.Tk()
    root.title("P4G Steam → Korean Vita Final Converter v1.0")
    root.geometry("970x820")
    root.minsize(850, 720)

    steam_var = tk.StringVar()
    vita_var = tk.StringVar()

    source_slot_var = tk.IntVar(value=1)
    target_slot_var = tk.IntVar(value=1)

    status_var = tk.StringVar(
        value="Steam 세이브와 vita-savemgr가 직접 만든 기존 PCSH00021 SLOT을 선택하세요."
    )

    frame = ttk.Frame(root, padding=14)
    frame.pack(fill="both", expand=True)

    frame.columnconfigure(1, weight=1)
    frame.rowconfigure(13, weight=1)

    ttk.Label(
        frame,
        text="Persona 4 Golden  Steam → 한국 Vita PCSH00021",
        font=("Segoe UI", 15, "bold"),
    ).grid(
        row=0,
        column=0,
        columnspan=4,
        sticky="w",
    )

    ttk.Label(
        frame,
        text=(
            "Final Converter v1.0 · 실제 한국판 파일에서 검증된 FULL_EXCEPT_0044 규칙 사용"
        ),
    ).grid(
        row=1,
        column=0,
        columnspan=4,
        sticky="w",
        pady=(2, 14),
    )

    ttk.Label(
        frame,
        text="Steam P4G remote 폴더",
    ).grid(
        row=2,
        column=0,
        sticky="w",
    )

    ttk.Entry(
        frame,
        textvariable=steam_var,
    ).grid(
        row=2,
        column=1,
        sticky="ew",
        padx=6,
    )

    def choose_steam():
        p = filedialog.askdirectory(
            parent=root,
            title="Steam Persona 4 Golden remote 폴더",
            mustexist=True,
        )

        if p:
            steam_var.set(p)
            refresh_info()

    ttk.Button(
        frame,
        text="찾아보기",
        command=choose_steam,
    ).grid(
        row=2,
        column=2,
        padx=3,
    )

    def auto_steam():
        found = find_steam_candidates()

        if not found:
            messagebox.showinfo(
                "자동 찾기",
                "Steam P4G 세이브 폴더를 찾지 못했습니다.",
                parent=root,
            )
            return

        steam_var.set(str(found[0]))
        refresh_info()

    ttk.Button(
        frame,
        text="자동 찾기",
        command=auto_steam,
    ).grid(
        row=2,
        column=3,
        padx=3,
    )

    ttk.Label(
        frame,
        text="기존 vita-savemgr SLOTn",
    ).grid(
        row=3,
        column=0,
        sticky="w",
        pady=5,
    )

    ttk.Entry(
        frame,
        textvariable=vita_var,
    ).grid(
        row=3,
        column=1,
        sticky="ew",
        padx=6,
    )

    def choose_vita():
        p = filedialog.askdirectory(
            parent=root,
            title=r"vita-savemgr가 직접 만든 PCSH00021\SLOTn 선택",
            mustexist=True,
        )

        if p:
            vita_var.set(p)
            refresh_info()

    ttk.Button(
        frame,
        text="찾아보기",
        command=choose_vita,
    ).grid(
        row=3,
        column=2,
        padx=3,
    )

    def auto_vita():
        found = find_vita_candidates()

        if not found:
            messagebox.showinfo(
                "자동 찾기",
                "연결된 드라이브에서 PCSH00021 vita-savemgr SLOT을 찾지 못했습니다.",
                parent=root,
            )
            return

        vita_var.set(str(found[0]))
        refresh_info()

    ttk.Button(
        frame,
        text="자동 찾기",
        command=auto_vita,
    ).grid(
        row=3,
        column=3,
        padx=3,
    )

    ttk.Separator(frame).grid(
        row=4,
        column=0,
        columnspan=4,
        sticky="ew",
        pady=12,
    )

    ttk.Label(
        frame,
        text="Steam 원본 게임 슬롯",
    ).grid(
        row=5,
        column=0,
        sticky="w",
    )

    steam_slot_combo = ttk.Combobox(
        frame,
        textvariable=source_slot_var,
        state="readonly",
        width=10,
    )
    steam_slot_combo.grid(
        row=5,
        column=1,
        sticky="w",
        padx=6,
    )

    ttk.Label(
        frame,
        text="Vita 대상 게임 슬롯",
    ).grid(
        row=6,
        column=0,
        sticky="w",
        pady=5,
    )

    vita_slot_combo = ttk.Combobox(
        frame,
        textvariable=target_slot_var,
        state="readonly",
        width=10,
    )
    vita_slot_combo.grid(
        row=6,
        column=1,
        sticky="w",
        padx=6,
    )

    ttk.Button(
        frame,
        text="다시 검사",
        command=lambda: refresh_info(),
    ).grid(
        row=6,
        column=3,
        sticky="e",
    )

    info_text = (
        "변환 규칙\n"
        "• 한국판 이름 버퍼 2개 유지\n"
        "• 한국판 고유 구조값 KR 0x44 유지\n"
        "• 그 외 KR 0x15100 이전 게임 상태는 Steam 세이브에서 이식\n"
        "• KR 0x15100 이후 Rescue / Retry / tail은 한국판 원본 그대로 유지\n"
        "• sdslot.dat / system.bin / checksum byte는 수정하지 않음\n"
        "• 새 SLOT 폴더를 만들지 않고 vita-savemgr가 직접 만든 기존 SLOT을 in-place 수정"
    )

    ttk.Label(
        frame,
        text=info_text,
        justify="left",
        wraplength=920,
    ).grid(
        row=8,
        column=0,
        columnspan=4,
        sticky="w",
        pady=(12, 10),
    )

    ttk.Separator(frame).grid(
        row=9,
        column=0,
        columnspan=4,
        sticky="ew",
        pady=(0, 8),
    )

    ttk.Label(
        frame,
        text="검증 / 변환 로그",
    ).grid(
        row=12,
        column=0,
        columnspan=4,
        sticky="w",
    )

    logbox = tk.Text(
        frame,
        height=20,
        state="disabled",
        wrap="word",
        font=("Consolas", 9),
    )
    logbox.grid(
        row=13,
        column=0,
        columnspan=4,
        sticky="nsew",
    )

    def log(msg: str):
        logbox.configure(state="normal")
        logbox.insert("end", msg + "\n")
        logbox.see("end")
        logbox.configure(state="disabled")
        root.update_idletasks()

    ttk.Label(
        frame,
        textvariable=status_var,
        wraplength=920,
    ).grid(
        row=14,
        column=0,
        columnspan=4,
        sticky="w",
        pady=(8, 4),
    )

    def refresh_info():
        log("=" * 76)

        # Steam side
        try:
            steam = Path(steam_var.get()).expanduser().resolve()
            steam_slots = discover_steam_slots(steam)

            steam_slot_combo["values"] = steam_slots

            if steam_slots:
                if source_slot_var.get() not in steam_slots:
                    source_slot_var.set(steam_slots[0])

                log(
                    "Steam 슬롯: "
                    + ", ".join(f"{n:02d}" for n in steam_slots)
                )

                n = source_slot_var.get()
                meta = parse_binslot_metadata(
                    steam / f"data00{n:02}.binslot"
                )

                log(
                    f"Steam slot {n:02d}: "
                    f"Date={meta.get('date') or '?'} | "
                    f"Difficulty={meta.get('difficulty') or '?'} | "
                    f"Play={meta.get('play_time') or '?'} | "
                    f"Times Cleared={meta.get('times_cleared') or '?'}"
                )

                if meta.get("ending"):
                    log(f"  {meta['ending']}")

            else:
                log("Steam: 유효한 data00XX.bin/.binslot 쌍을 찾지 못함")

        except Exception as exc:
            steam_slot_combo["values"] = ()
            log("Steam 검사 실패: " + str(exc))

        # Vita side
        try:
            slot = validate_existing_savemgr_slot(
                Path(vita_var.get())
            )

            vita_slots = discover_vita_game_slots(slot)
            vita_slot_combo["values"] = vita_slots

            if vita_slots:
                if target_slot_var.get() not in vita_slots:
                    target_slot_var.set(vita_slots[0])

                log(
                    f"Vita {slot.name} 활성 게임 슬롯: "
                    + ", ".join(f"{n:02d}" for n in vita_slots)
                )

                status_var.set(
                    "검증 완료. 변환 전 대상 SLOT 전체가 자동 ZIP 백업됩니다."
                )

            else:
                log("Vita: 활성 한국판 게임 슬롯을 찾지 못함")

        except Exception as exc:
            vita_slot_combo["values"] = ()
            log("Vita 검사 실패: " + str(exc))

    def convert():
        convert_btn.configure(state="disabled")

        try:
            steam = Path(steam_var.get()).expanduser().resolve()
            vita_slot = validate_existing_savemgr_slot(
                Path(vita_var.get())
            )

            src_n = int(source_slot_var.get())
            dst_n = int(target_slot_var.get())

            pc_data_path = steam / f"data00{src_n:02}.bin"
            pc_binslot_path = steam / f"data00{src_n:02}.binslot"

            if not pc_data_path.is_file() or not pc_binslot_path.is_file():
                raise ConverterError(
                    f"Steam slot {src_n:02} 파일쌍이 없습니다."
                )

            verify_binslot_pair(pc_data_path, pc_binslot_path)

            pc = pc_data_path.read_bytes()
            validate_steam_data(pc, pc_data_path.name)

            target_path = vita_slot / f"data00{dst_n:02}.bin"

            if not target_path.is_file():
                raise ConverterError(
                    f"Vita 대상 data00{dst_n:02}.bin이 없습니다."
                )

            kr = target_path.read_bytes()
            validate_korean_data(kr, target_path.name)

            metadata = parse_binslot_metadata(pc_binslot_path)

            confirmation = (
                "다음 세이브를 변환합니다.\n\n"
                f"Steam source: slot {src_n:02d}\n"
                f"  Date: {metadata.get('date') or '?'}\n"
                f"  Play Time: {metadata.get('play_time') or '?'}\n"
                f"  Times Cleared: {metadata.get('times_cleared') or '?'}\n\n"
                f"Korean Vita target:\n"
                f"  {vita_slot}\n"
                f"  game slot {dst_n:02d}\n\n"
                "대상 vita-savemgr SLOT 전체를 먼저 ZIP 백업한 뒤 "
                "data 파일만 in-place로 변환합니다.\n\n"
                "계속할까요?"
            )

            if not messagebox.askyesno(
                "Steam → Korean Vita 변환",
                confirmation,
                parent=root,
            ):
                return

            backup = create_zip_backup(
                vita_slot,
                note=(
                    f"before final converter Steam slot {src_n:02d} "
                    f"to Vita game slot {dst_n:02d}"
                ),
            )

            log("=" * 76)
            log(f"자동 백업: {backup}")
            log(
                f"변환: Steam data00{src_n:02}.bin "
                f"-> Vita data00{dst_n:02}.bin"
            )

            original_sd_hash = sha256_file(
                vita_slot / "sce_sys" / "sdslot.dat"
            )

            system_path = vita_slot / "system.bin"
            original_system_hash = (
                sha256_file(system_path)
                if system_path.is_file()
                else None
            )

            old_hash = hashlib.sha256(kr).hexdigest()
            result = convert_data(pc, kr)
            new_hash = hashlib.sha256(result).hexdigest()

            changed = sum(
                1
                for a, b in zip(kr, result)
                if a != b
            )

            atomic_write(target_path, result)

            if target_path.read_bytes() != result:
                raise ConverterError(
                    "쓰기 후 data 파일 검증 실패"
                )

            # Files that must remain untouched.
            if sha256_file(
                vita_slot / "sce_sys" / "sdslot.dat"
            ) != original_sd_hash:
                raise ConverterError(
                    "안전 검증 실패: sdslot.dat가 변경되었습니다."
                )

            if original_system_hash is not None:
                if (
                    not system_path.is_file()
                    or sha256_file(system_path) != original_system_hash
                ):
                    raise ConverterError(
                        "안전 검증 실패: system.bin이 변경되었습니다."
                    )

            log(f"변경 바이트 수: {changed:,}")
            log(f"변환 전 data SHA-256: {old_hash}")
            log(f"변환 후 data SHA-256: {new_hash}")
            log(f"KR 0x44 보존값: 0x{result[0x44]:02X}")
            log(
                "한국판 name buffers / Rescue / Retry / "
                "sdslot.dat / system.bin 보존 검증 통과"
            )

            status_var.set(
                "변환 완료. Vita에서 방금 수정한 SAME savemgr SLOT을 Restore하세요."
            )

            messagebox.showinfo(
                "변환 완료",
                "Steam → 한국 Vita 세이브 변환이 완료되었습니다.\n\n"
                f"자동 백업:\n{backup}\n\n"
                "Vita에서 새 SLOT을 만들거나 찾지 말고, "
                "방금 수정한 SAME vita-savemgr SLOT을 Restore하세요.\n\n"
                "LOAD 화면 메타데이터는 기존 한국판 표시가 남을 수 있습니다. "
                "게임에서 정상 로드 후 한 번 다시 저장하면 게임이 자체적으로 "
                "메타데이터를 갱신합니다.",
                parent=root,
            )

        except Exception as exc:
            status_var.set("변환 실패")
            log("ERROR: " + str(exc))
            log(traceback.format_exc())

            messagebox.showerror(
                "변환 실패",
                str(exc),
                parent=root,
            )

        finally:
            convert_btn.configure(state="normal")

    def restore_backup():
        try:
            zip_name = filedialog.askopenfilename(
                parent=root,
                title="P4G_Vita_Backups ZIP 선택",
                filetypes=[
                    ("ZIP backup", "*.zip"),
                    ("All files", "*.*"),
                ],
            )

            if not zip_name:
                return

            target_name = filedialog.askdirectory(
                parent=root,
                title=r"복원할 기존 PCSH00021\SLOTn 선택",
                mustexist=True,
            )

            if not target_name:
                return

            target = validate_existing_savemgr_slot(
                Path(target_name)
            )

            if not messagebox.askyesno(
                "백업 복원",
                f"다음 기존 SLOT을 ZIP 백업 상태로 되돌립니다.\n\n"
                f"대상:\n{target}\n\n"
                f"백업:\n{zip_name}\n\n"
                "현재 상태도 복원 전에 자동 백업됩니다.\n"
                "계속할까요?",
                parent=root,
            ):
                return

            restore_backup_zip(
                Path(zip_name),
                target,
            )

            status_var.set("ZIP 백업 복원 완료")

            messagebox.showinfo(
                "복원 완료",
                "선택한 기존 vita-savemgr SLOT을 ZIP 백업 상태로 복원했습니다.",
                parent=root,
            )

        except Exception as exc:
            log("RESTORE ERROR: " + str(exc))
            log(traceback.format_exc())

            messagebox.showerror(
                "복원 실패",
                str(exc),
                parent=root,
            )

    convert_btn = ttk.Button(
        frame,
        text="Steam → 한국 Vita 세이브 변환",
        command=convert,
    )
    convert_btn.grid(
        row=15,
        column=0,
        columnspan=3,
        sticky="ew",
        pady=(8, 0),
        ipady=8,
    )

    ttk.Button(
        frame,
        text="ZIP 백업 복원",
        command=restore_backup,
    ).grid(
        row=15,
        column=3,
        sticky="ew",
        padx=(6, 0),
        pady=(8, 0),
        ipady=8,
    )

    # Best-effort auto detection.
    try:
        found = find_steam_candidates()
        if found:
            steam_var.set(str(found[0]))
    except Exception:
        pass

    try:
        found = find_vita_candidates()
        if found:
            vita_var.set(str(found[0]))
    except Exception:
        pass

    if steam_var.get() or vita_var.get():
        try:
            refresh_info()
        except Exception:
            pass

    root.mainloop()


if __name__ == "__main__":
    run_gui()
