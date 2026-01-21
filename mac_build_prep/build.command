#!/bin/bash
cd "$(dirname "$0")"

echo "=========================================="
echo "   YouTube Downloader macOS 自動打包腳本"
echo "=========================================="
echo "正在準備環境..."

# 1. 檢查並建立虛擬環境 (避免影響系統設定)
if [ ! -d "venv" ]; then
    echo "正在建立 Python 虛擬環境..."
    python3 -m venv venv
fi

# 啟動虛擬環境
source venv/bin/activate

# 2. 安裝 PyInstaller
echo "正在安裝打包工具 (PyInstaller)..."
pip install pyinstaller --quiet

# 3. 準備 bin 資料夾
mkdir -p bin

# 4. 自動下載 yt-dlp (macOS 版本)
echo "正在下載 yt-dlp..."
curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_macos -o bin/yt-dlp
chmod +x bin/yt-dlp

# 5. 自動下載 ffmpeg (macOS 版本)
echo "正在下載 FFmpeg..."
curl -L https://evermeet.cx/ffmpeg/getrelease/zip -o ffmpeg.zip
unzip -o -q ffmpeg.zip -d bin
rm ffmpeg.zip
chmod +x bin/ffmpeg

# 移除 macOS 安全隔離屬性 (避免無法執行)
echo "正在處理檔案權限..."
xattr -d com.apple.quarantine bin/yt-dlp 2>/dev/null
xattr -d com.apple.quarantine bin/ffmpeg 2>/dev/null

# 6. 開始打包
echo "正在打包應用程式，請稍候..."
pyinstaller --name "YouTubeDownloader" --onefile --windowed --add-data "bin:bin" main.py

echo "=========================================="
echo "   打包完成！"
echo "=========================================="
echo "應用程式位於 'dist' 資料夾中。"
echo "正在開啟資料夾..."

open dist
