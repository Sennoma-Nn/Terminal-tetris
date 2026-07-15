#!/bin/bash
set -e

PKG_NAME="terminal-tetris"
PKG_VERSION="1.1.0"
ARCH="all"
MAINTAINER="kimt223 <kim20100223@outlook.com>"
# 在标准 Linux 系统中，Python 3 的包名通常是 python3，mpv 保持不变
DEPENDS="python3, mpv"

BUILD_DIR="./deb-build"
DEB_FILE="${PKG_NAME}_${PKG_VERSION}_${ARCH}.deb"

# 清理并创建符合标准 Linux FHS 规范的目录结构
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR/DEBIAN"
mkdir -p "$BUILD_DIR/usr/bin"
mkdir -p "$BUILD_DIR/usr/share/terminal-tetris"

# 1. 复制游戏主程序和音频资源到标准的共享资源目录
cp ./tetris.py "$BUILD_DIR/usr/share/terminal-tetris/tetris.py"
if [ -f "./tetris.mp3" ]; then
    cp ./tetris.mp3 "$BUILD_DIR/usr/share/terminal-tetris/tetris.mp3"
fi

# 2. 生成标准的启动脚本，使用 /bin/sh，并调用系统的 python3
cat > "$BUILD_DIR/usr/bin/terminal-tetris" << 'EOF'
#!/bin/sh
# 切换到共享资源目录以正确读取当前目录下的音频文件
cd /usr/share/terminal-tetris || exit 1
exec python3 tetris.py "$@"
EOF
chmod +x "$BUILD_DIR/usr/bin/terminal-tetris"

# 3. 生成标准的 Debian 控制文件
cat > "$BUILD_DIR/DEBIAN/control" << EOF
Package: $PKG_NAME
Version: $PKG_VERSION
Section: games
Priority: optional
Architecture: $ARCH
Maintainer: $MAINTAINER
Depends: $DEPENDS
Description: Terminal Tetris Game
 A fully featured retro Tetris game running right in your terminal.
 Built with Python's native curses library, supporting optional background
 music via mpv player and ghost piece preview.
EOF

# 4. 严格修正权限（Debian 打包安全规范）
# 目录权限通常为 755，普通文件为 644
find "$BUILD_DIR" -type d -exec chmod 755 {} +
find "$BUILD_DIR" -type f -exec chmod 644 {} +
# 恢复可执行文件的权限
chmod 755 "$BUILD_DIR/usr/bin/terminal-tetris"
chmod 755 "$BUILD_DIR/usr/share/terminal-tetris/tetris.py"

# 5. 构建包体
dpkg-deb --build "$BUILD_DIR" "$DEB_FILE"
rm -rf "$BUILD_DIR"

echo ""
echo "✅ 标准 DEB 打包完成: $DEB_FILE"
echo "安装命令: sudo dpkg -i $DEB_FILE"
echo "卸载命令: sudo apt remove $PKG_NAME"
echo "运行命令: terminal-tetris"

