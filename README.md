# Terminal-tetris

一个运行在终端里的俄罗斯方块游戏，使用 Python 内置 `curses` 库实现，无需额外依赖。

## 特性

- **SRS 旋转系统**：完整的 Super Rotation System，支持 Wall Kick
- **7-Bag 随机生成器**：保证每 7 块必出一次完整套装
- **Hold 功能**：按 `C`/`H` 暂存当前方块
- **Ghost 影子**：显示方块落点预览
- **Lock Delay**：落地延迟锁定，支持无限重置（上限 15 次）
- **等级加速**：消行升级，速度逐渐加快。
