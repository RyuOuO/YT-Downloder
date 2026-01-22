# YouTube Downloader macOS 懶人打包指南

本腳本會自動下載工具、打包程式，並產生可直接安裝的 `.pkg` 檔。

## 使用方法

1. **複製**：
   將 `mac_build_prep` 整個資料夾複製到您的 Mac 電腦上。

2. **執行**：
   在 Mac 上進入該資料夾，**點擊兩下** `build.command`。
   (如果無法執行，請在終端機輸入 `chmod +x build.command` 授權後再試)

3. **安裝**：
   腳本執行完畢後，會自動開啟 `dist` 資料夾。
   - `YouTubeDownloader.app`：免安裝版，直接執行。
   - `YouTubeDownloader.pkg`：**安裝檔**，雙擊即可將程式安裝到您的「應用程式」資料夾中。

## 常見問題
- **"無法打開未識別開發者的程式"**：
  請到 Mac 的「系統設定」>「隱私權與安全性」，在下方點擊「強制打開 (Open Anyway)」。
