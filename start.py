"""从解压目录运行当前 Web 项目，不依赖原来的 E 盘路径。"""
import json
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
URL = "http://127.0.0.1:5000"


def is_running():
    try:
        with urllib.request.urlopen(URL + "/api/rules", timeout=1) as response:
            rules = json.load(response)
        return isinstance(rules, list) and len(rules) == 18
    except Exception:
        return False


def open_when_ready():
    for _ in range(60):
        if is_running():
            webbrowser.open(URL + "/?scene=local&version=after&v=compare1")
            return
        time.sleep(.25)
    print("服务尚未就绪，请查看控制台错误。")


def main():
    if is_running():
        webbrowser.open(URL + "/?scene=local&version=after&v=compare1")
        print("已打开正在运行的风水 Web 服务。")
        return
    sys.path.insert(0, str(ROOT / "webapp"))
    from app import app
    print("启动地址：" + URL)
    print("关闭此窗口或按 Ctrl+C 可停止服务。")
    threading.Thread(target=open_when_ready, daemon=True).start()
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
