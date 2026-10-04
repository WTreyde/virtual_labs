import sys

from labforge.protocols import export

export(sys.argv[1] if len(sys.argv) > 1 else "protocols_export")
