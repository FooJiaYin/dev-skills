# 靜態檔伺服器，每個回應都帶 Cache-Control: no-store——給使用者驗收的本機網址用，改檔後一般重新整理就看得到新版。
# Usage: python3 serve-nocache.py <dir> [port=8831]
import functools, http.server, sys

class H(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

d = sys.argv[1]
port = int(sys.argv[2]) if len(sys.argv) > 2 else 8831
print(f"http://127.0.0.1:{port}/  ← {d}")
http.server.ThreadingHTTPServer(("127.0.0.1", port), functools.partial(H, directory=d)).serve_forever()
