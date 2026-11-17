import importlib.util
import json
from pathlib import Path
import socket
import sys
import threading
import types
import unittest

# Test transport in isolation; importing it must not require a CUDA runtime.
sys.modules.setdefault("pearl_mining", types.ModuleType("pearl_mining"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))
from pool_common import HeroMiners, DEV_FEE

JOB = {"job_id": "sample", "header": "00" * 76, "target": "00000000000007fff80000000000000000000000000000000000000000000000", "cert_version": 3}

class ProtocolTests(unittest.TestCase):
    def test_job_validation(self):
        p = HeroMiners("localhost", 1, "wallet", "worker")
        header, target, jid = p.parse_job(JOB)
        self.assertEqual(len(header), 76)
        self.assertGreater(target, 0)
        self.assertEqual(jid, "sample")
        for update in ({"cert_version": 4}, {"header": "00"}, {"target": "0"}, {"job_id": ""}):
            with self.assertRaises(ConnectionError):
                p.parse_job(dict(JOB, **update))
        self.assertEqual(DEV_FEE, 0.02)

    def test_authorize_job_submit_and_close(self):
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        errors = []
        def server():
            try:
                with listener.accept()[0] as conn:
                    conn.settimeout(3)
                    f = conn.makefile("rb")
                    auth = json.loads(f.readline())
                    assert auth["params"] == {"wallet": "wallet", "worker": "worker"}
                    # A job before the auth response must remain buffered.
                    conn.sendall((json.dumps({"method":"mining.notify", "params":JOB}) + "\n" + json.dumps({"id":1,"result":True,"error":None}) + "\n").encode())
                    submit = json.loads(f.readline())
                    assert submit["method"] == "mining.submit"
                    assert submit["params"] == {"wallet":"wallet","worker":"worker","job_id":"sample","plain_proof":"test-proof"}
                    conn.sendall(b'{"id":99,"result":true,"error":null}\n')
            except Exception as e:
                errors.append(e)
        t = threading.Thread(target=server, daemon=True)
        t.start()
        p = HeroMiners("127.0.0.1", listener.getsockname()[1], "wallet", "worker")
        try:
            p.connect()
            self.assertEqual(p.next_job()[2], "sample")
            self.assertTrue(p.submit("sample", "test-proof")["result"])
        finally:
            p.close()
            listener.close()
            t.join(4)
        self.assertFalse(t.is_alive())
        self.assertEqual(errors, [])

    def test_rejected_authorization_closes_socket(self):
        p = HeroMiners("localhost", 1, "wallet", "worker")
        from unittest.mock import patch, MagicMock
        connection = MagicMock()
        connection.recv.return_value = b'{"id":1,"result":false,"error":{"code":20}}\n'
        with patch("socket.create_connection", return_value=connection):
            with self.assertRaises(ConnectionError):
                p.connect()
        connection.close.assert_called_once()
        self.assertIsNone(p.s)
