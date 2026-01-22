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
$PYTHON_EXEC -m pip install pyinstaller instaloader certifi Pillow ttkbootstrap --quiet

# 3. 準備 bin 資料夾
mkdir -p bin

# ... (skip download section) ...

# 移除 macOS 安全隔離屬性 (避免無法執行)
echo "正在處理檔案權限..."
xattr -d com.apple.quarantine bin/yt-dlp 2>/dev/null
xattr -d com.apple.quarantine bin/ffmpeg 2>/dev/null

# 取得 PIL 安裝路徑
PIL_PATH=$($PYTHON_EXEC -c "import PIL; import os; print(os.path.dirname(PIL.__file__))")
echo "PIL 路徑: $PIL_PATH"

# 取得 ttkbootstrap 安裝路徑
TTK_PATH=$($PYTHON_EXEC -c "import ttkbootstrap; import os; print(os.path.dirname(ttkbootstrap.__file__))")
echo "ttkbootstrap 路徑: $TTK_PATH"

# 6. 開始打包
echo "正在打包應用程式，請稍候..."
# 清理舊的 build
rm -rf build dist *.spec
$PYTHON_EXEC -m PyInstaller --name "YouTubeDownloader" --onefile --windowed --add-data "bin:bin" --add-data "$PIL_PATH:PIL" --add-data "$TTK_PATH:ttkbootstrap" --paths "$PIL_PATH" --paths "$TTK_PATH" --hidden-import=PIL --hidden-import=PIL._tkinter_finder --hidden-import=PIL.Image --hidden-import=PIL.ImageTk --hidden-import=ttkbootstrap main.py

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