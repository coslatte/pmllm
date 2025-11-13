import tarfile
from pathlib import Path

TAR_FILE = Path("D:\_Temporary\mbdump.tar.bz2")

with tarfile.open(TAR_FILE, "r|*") as tar:
    print(tar.getnames())
