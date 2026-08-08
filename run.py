import uvicorn
import webbrowser
import threading
import time

def open_browser():
    time.sleep(1.5)
    webbrowser.open("http://127.0.0.1:8000")

if __name__ == "__main__":
    print("啟動 Website Crawler Web 應用...")
    print("訪問網址: http://127.0.0.1:8000")
    threading.Thread(target=open_browser, daemon=True).start()
    uvicorn.run("src.app:app", host="127.0.0.1", port=8000, reload=False)
