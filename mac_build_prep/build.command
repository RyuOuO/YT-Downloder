#!/bin/bash
cd "$(dirname "$0")"

echo "=========================================="
echo "   YouTube Downloader macOS 自動打包腳本"
echo "=========================================="
echo "正在準備環境..."

# 1. 檢查並建立虛擬環境
if [ ! -d "venv" ]; then
    echo "正在建立 Python 虛擬環境..."
    python3 -m venv venv
fi

# 啟動虛擬環境 (Optional, but using direct path is safer)
# source venv/bin/activate
PYTHON_EXEC="venv/bin/python"

# 2. 安裝 PyInstaller 和 Instaloader
echo "正在安裝依賴套件..."
$PYTHON_EXEC -m pip install pyinstaller instaloader certifi Pillow --quiet

# 3. 準備 bin 資料夾
mkdir -p bin

# 4. 自動下載 yt-dlp (macOS 版本)
if [ ! -f "bin/yt-dlp" ]; then
    echo "正在下載 yt-dlp..."
    curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_macos -o bin/yt-dlp
    chmod +x bin/yt-dlp
fi

# 5. 自動下載 ffmpeg (macOS 版本)
if [ ! -f "bin/ffmpeg" ]; then
    echo "正在下載 FFmpeg..."
    curl -L https://evermeet.cx/ffmpeg/getrelease/zip -o ffmpeg.zip
    unzip -o -q ffmpeg.zip -d bin
    rm ffmpeg.zip
    chmod +x bin/ffmpeg
fi

# 移除 macOS 安全隔離屬性 (避免無法執行)
echo "正在處理檔案權限..."
xattr -d com.apple.quarantine bin/yt-dlp 2>/dev/null
xattr -d com.apple.quarantine bin/ffmpeg 2>/dev/null

# 取得 PIL 安裝路徑
PIL_PATH=$($PYTHON_EXEC -c "import PIL; import os; print(os.path.dirname(PIL.__file__))")
echo "PIL 路徑: $PIL_PATH"

# 6. 開始打包
echo "正在打包應用程式，請稍候..."
# 清理舊的 build
rm -rf build dist *.spec
$PYTHON_EXEC -m PyInstaller --name "YouTubeDownloader" --onefile --windowed --add-data "bin:bin" --add-data "$PIL_PATH:PIL" --paths "$PIL_PATH" --hidden-import=PIL --hidden-import=PIL._tkinter_finder --hidden-import=PIL.Image --hidden-import=PIL.ImageTk main.py

# 7. 製作 .pkg 安裝檔
echo "------------------------------------------"
echo "正在製作 .pkg 安裝檔..."

if [ -d "dist/YouTubeDownloader.app" ]; then
    # 使用 pkgbuild 建立安裝包，預設安裝到 /Applications
    pkgbuild --install-location /Applications --component "dist/YouTubeDownloader.app" "dist/YouTubeDownloader.pkg"
    
    echo "=========================================="
    echo "   打包全部完成！"
    echo "=========================================="
    echo "您的安裝檔位於： dist/YouTubeDownloader.pkg"
else
    echo "錯誤：找不到 .app 檔案，由 PyInstaller 打包失敗。"
fi

echo "正在開啟輸出資料夾..."
open dist