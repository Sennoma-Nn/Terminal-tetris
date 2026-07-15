#!/bin/bash
set -e

PKG_NAME="terminal-tetris"
PKG_VERSION="1.1.0"
PKG_RELEASE="1"
ARCH="noarch" # RPM 中纯 Python 架构通常称为 noarch

RPM_TOPDIR="$(pwd)/rpm-build"
rm -rf "$RPM_TOPDIR"
mkdir -p "$RPM_TOPDIR"/{BUILD,RPMS,SOURCES,SPECS,SRPMS,BUILDROOT}

# 1. 准备源码目录
SRC_DIR="$RPM_TOPDIR/BUILD/${PKG_NAME}-${PKG_VERSION}"
mkdir -p "$SRC_DIR/usr/bin"
mkdir -p "$SRC_DIR/usr/share/terminal-tetris"

# 2. 复制游戏主程序和音频资源
cp ./tetris.py "$SRC_DIR/usr/share/terminal-tetris/tetris.py"
if [ -f "./tetris.mp3" ]; then
    cp ./tetris.mp3 "$SRC_DIR/usr/share/terminal-tetris/tetris.mp3"
fi

# 3. 生成标准的启动脚本
cat > "$SRC_DIR/usr/bin/terminal-tetris" << 'EOF'
#!/bin/sh
cd /usr/share/terminal-tetris || exit 1
exec python3 tetris.py "$@"
EOF
chmod +x "$SRC_DIR/usr/bin/terminal-tetris"

# 4. 生成 RPM Spec 文件
cat > "$RPM_TOPDIR/SPECS/${PKG_NAME}.spec" << EOF
Name:           ${PKG_NAME}
Version:        ${PKG_VERSION}
Release:        ${PKG_RELEASE}%{?dist}
Summary:        Terminal Tetris Game
Group:          Amusements/Games
License:        MIT
URL:            https://example.com/tetris
BuildArch:      ${ARCH}

Requires:       python3
Requires:       mpv

%description
A fully featured retro Tetris game running right in your terminal.
Built with Python's native curses library, supporting optional background
music via mpv player and ghost piece preview.

%prep
# 我们已经手动把文件放到了 BUILD 目录下，所以不需要 %setup 解压

%build
# 纯脚本语言，无需编译

%install
rm -rf %{buildroot}
mkdir -p %{buildroot}/usr/bin
mkdir -p %{buildroot}/usr/share/terminal-tetris

cp -r $RPM_TOPDIR/BUILD/${PKG_NAME}-${PKG_VERSION}/usr/bin/* %{buildroot}/usr/bin/
cp -r $RPM_TOPDIR/BUILD/${PKG_NAME}-${PKG_VERSION}/usr/share/terminal-tetris/* %{buildroot}/usr/share/terminal-tetris/

%clean
rm -rf %{buildroot}

%files
%defattr(-,root,root,-)
/usr/bin/terminal-tetris
/usr/share/terminal-tetris/

%changelog
* Mon Jul 13 2026 Your Name <you@example.com> - 1.0.1-1
- Initial RPM release for standard Linux distributions.
EOF

# 5. 构建 RPM 包
# --define 用于强制指定工作目录，避免污染系统的 ~/rpmbuild
rpmbuild --define "_topdir $RPM_TOPDIR" -bb "$RPM_TOPDIR/SPECS/${PKG_NAME}.spec"

# 6. 把生成的二进制包移出来并清理
cp "$RPM_TOPDIR"/RPMS/noarch/*.rpm ./
rm -rf "$RPM_TOPDIR"

echo ""
echo "✅ 标准 RPM 打包完成!"
echo "安装命令: sudo rpm -ivh ${PKG_NAME}-${PKG_VERSION}-${PKG_RELEASE}.*.noarch.rpm"
echo "或者使用: sudo dnf install ./${PKG_NAME}-${PKG_VERSION}-${PKG_RELEASE}.*.noarch.rpm"
echo "运行命令: terminal-tetris"

