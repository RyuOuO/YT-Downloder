# YouTube Downloader

一個簡單易用的 YouTube 影片與音樂下載器，支援 Windows 與 macOS。

## 功能特色
- **跨平台**：支援 Windows (.exe) 與 macOS (.app)。
- **簡單介面**：圖形化操作，輕鬆貼上網址即可下載。
- **多種格式**：支援下載高品質影片 (MP4/MKV) 或純音訊 (MP3)。
- **播放清單支援**：自動偵測播放清單，智慧下載不重複。
- **進度顯示**：即時顯示下載進度條與日誌。

## 開發環境設定

### 前置需求
- Python 3.10+
- Node.js (yt-dlp 需要 JavaScript 執行環境)

### 安裝依賴
```bash
pip install pyinstaller
```

### 準備工具 (Windows)
1. 在專案根目錄建立 `bin` 資料夾。
2. 下載 [yt-dlp.exe](https://github.com/yt-dlp/yt-dlp/releases) 放入 `bin/`。
3. 下載 [ffmpeg.exe](https://gyan.dev/ffmpeg/builds/) 放入 `bin/`。

### 執行程式
```bash
python src/main.py
```

## 打包應用程式

### Windows
執行以下指令產生 `.exe` 檔：
```bash
pyinstaller --name yt_downloader --onefile --windowed --add-data "bin;bin" src/main.py
```
執行檔將位於 `dist/` 資料夾。

### macOS
請參考 `mac_build_prep/README_MAC.txt` 中的詳細說明，或直接使用該資料夾內的懶人腳本。

## 授權
MIT License
