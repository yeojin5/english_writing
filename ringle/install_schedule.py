#!/usr/bin/env python3
"""ringle_sync.py sync 를 매일 정해진 시간에 실행하도록 등록합니다.

  python ringle/install_schedule.py            # 매일 23:00 (기본)
  python ringle/install_schedule.py --time 21:30
  python ringle/install_schedule.py --remove

- Windows: 작업 스케줄러. 그 시간에 컴퓨터가 꺼져 있었으면 켜진 뒤 바로 실행합니다.
- Mac: launchd. 잠자기 중이었으면 깨어난 뒤 실행합니다.
"""
import argparse
import platform
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "ringle_sync.py"
NAME = "RingleSync"
LABEL = "com.english-writing.ringle-sync"
PLIST = Path.home() / "Library/LaunchAgents" / f"{LABEL}.plist"
LOGDIR = Path.home() / ".ringle_sync"


def windows(hh: int, mm: int, remove: bool) -> None:
    if remove:
        subprocess.run(["powershell", "-NoProfile", "-Command",
                        f"Unregister-ScheduledTask -TaskName {NAME} -Confirm:$false"], check=False)
        print("삭제했어요.")
        return
    py = Path(sys.executable).with_name("pythonw.exe")  # 콘솔 창 안 뜨게
    if not py.exists():
        py = Path(sys.executable)
    ps = (
        f"$a = New-ScheduledTaskAction -Execute '{py}' -Argument '\"{SCRIPT}\" sync' -WorkingDirectory '{HERE.parent}';"
        f"$t = New-ScheduledTaskTrigger -Daily -At {hh:02d}:{mm:02d};"
        "$s = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries "
        "-ExecutionTimeLimit (New-TimeSpan -Hours 2);"
        f"Register-ScheduledTask -TaskName {NAME} -Action $a -Trigger $t -Settings $s -Force | Out-Null"
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True)
    print(f"✅ 작업 스케줄러에 '{NAME}' 등록: 매일 {hh:02d}:{mm:02d}")


def mac(hh: int, mm: int, remove: bool) -> None:
    subprocess.run(["launchctl", "unload", str(PLIST)], check=False, capture_output=True)
    if remove:
        PLIST.unlink(missing_ok=True)
        print("삭제했어요.")
        return
    LOGDIR.mkdir(parents=True, exist_ok=True)
    PLIST.parent.mkdir(parents=True, exist_ok=True)
    PLIST.write_text(f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>{LABEL}</string>
  <key>ProgramArguments</key><array>
    <string>{sys.executable}</string><string>{SCRIPT}</string><string>sync</string>
  </array>
  <key>WorkingDirectory</key><string>{HERE.parent}</string>
  <key>StartCalendarInterval</key><dict>
    <key>Hour</key><integer>{hh}</integer><key>Minute</key><integer>{mm}</integer>
  </dict>
  <key>StandardOutPath</key><string>{LOGDIR / 'launchd.out'}</string>
  <key>StandardErrorPath</key><string>{LOGDIR / 'launchd.err'}</string>
</dict></plist>
""", encoding="utf-8")
    subprocess.run(["launchctl", "load", str(PLIST)], check=True)
    print(f"✅ launchd 등록: 매일 {hh:02d}:{mm:02d} ({PLIST})")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--time", default="23:00", help="HH:MM (기본 23:00)")
    p.add_argument("--remove", action="store_true")
    a = p.parse_args()
    hh, mm = map(int, a.time.split(":"))
    system = platform.system()
    if system == "Windows":
        windows(hh, mm, a.remove)
    elif system == "Darwin":
        mac(hh, mm, a.remove)
    else:
        print(f"이 OS({system})는 cron 에 직접 등록해 주세요:\n"
              f"  {mm} {hh} * * * cd {HERE.parent} && {sys.executable} {SCRIPT} sync")


if __name__ == "__main__":
    main()
