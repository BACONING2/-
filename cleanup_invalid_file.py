from pathlib import Path

p = Path("c:/Users/baconing/Desktop/新建文件夹/import time.py")
print("exists_before=", p.exists())
if p.exists():
    p.unlink()
print("exists_after=", p.exists())
