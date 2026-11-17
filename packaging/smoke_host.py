"""No GPU search: check the real Rust bindings used to construct submissions."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))
import numpy as np
import pearl_host
from pool_common import real_config

cfg = real_config()
key = pearl_host.derive_key(bytes(76), cfg)
assert len(key) == 32
matrix = np.zeros((16, 4096), dtype=np.int8)
proof = pearl_host.build_proof_bt(matrix, matrix, 0, 0, key, 256)
assert proof.to_base64()
print("Real Rust binding API and proof serialization: OK (not a valid mining share)")
