# FOC PI参数整定辅助调参软件

## 项目概述

本项目是一个FOC（磁场定向控制）电机控制PI参数整定辅助调参软件，支持PMSM（永磁同步电机）的电流环和速度环PI参数整定。

**核心功能**：
- 离线PI参数整定计算
- 在线串口调试和波形监控
- AI大模型辅助智能调参
- 多平台代码生成（STM32/GD32/AT32/TI）

## 技术栈

- **语言**：Python 3.10+
- **GUI**：PyQt6 / Tkinter
- **串口通信**：pyserial
- **AI集成**：OpenAI API / 兼容接口
- **可视化**：matplotlib

## 目录结构

```
motor_para/
├── src/
│   ├── core/           # 核心算法层
│   │   ├── models.py   # 数据模型定义
│   │   ├── tuner.py    # 主整定器
│   │   ├── validator.py # 参数验证
│   │   └── algorithms/ # 整定算法实现
│   ├── ai/             # AI集成层
│   │   ├── engine.py   # AI决策引擎
│   │   └── providers/  # API适配
│   ├── platform/       # 平台适配层
│   │   ├── base.py     # 平台基类
│   │   └── stm32.py    # 具体平台实现
│   ├── comm/           # 通信层
│   │   ├── protocol.py # 协议实现
│   │   └── serial.py   # 串口通信
│   └── ui/             # 用户界面层
├── tests/              # 测试
├── config/             # 配置文件
└── docs/               # 文档
```

## 常用命令

```bash
# 安装依赖
pip install -r requirements.txt

# 运行测试
pytest tests/

# 启动应用
python -m src.ui.main_window

# 代码格式化
black src/ tests/

# 类型检查
mypy src/

# Lint检查
ruff check src/
```

## 开发规范

### 代码风格
- 使用Black格式化，行宽88
- 使用类型注解（Type Hints）
- 函数和类必须有docstring
- 变量命名：snake_case
- 类命名：PascalCase
- 常量命名：UPPER_SNAKE_CASE

### 命名约定
- 电机参数使用物理量符号：`Rs`, `Ld`, `Lq`, `Psi_f`, `J`, `p`
- PI参数：`Kp`, `Ki`
- 环路类型：`current_d`, `current_q`, `speed`

### 文件组织
- 每个模块单一职责
- 算法实现在 `algorithms/` 目录下独立文件
- 平台代码生成在 `platform/` 目录下
- AI相关在 `ai/` 目录下

## 核心原理

### PMSM数学模型

dq坐标系电压方程：
```
Vd = Rs·id + Ld·(did/dt) - ωe·Lq·iq
Vq = Rs·iq + Lq·(diq/dt) + ωe·(Ld·id + Ψf)
```

### PI整定公式

**电流环（带宽法）**：
```
Kp = ωc × L
Ki = ωc × R
```

**速度环（带宽法）**：
```
Kp = 2 × ζ × ωn × J / Kt
Ki = ωn² × J / Kt
```

## 串口协议

- 帧格式：`HEAD(0xAA) + LEN(2B) + CMD(1B) + DATA(nB) + CRC(2B) + TAIL(0x55)`
- 波特率：115200（默认）
- 数据格式：8N1

## 平台支持

| 平台 | 代码风格 | 定点支持 |
|-----|---------|---------|
| STM32 F4/G4/H7 | HAL/LL | 浮点/Q格式 |
| GD32 | 标准库/HAL | 浮点/Q格式 |
| AT32 | 标准库 | 浮点 |
| TI C2000 | DriverLib | IQ格式 |

## 注意事项

- AI建议仅供参考，最终参数需人工确认
- 参数计算结果需标注置信度
- 在线调试前确保安全环境
- 定点数计算注意溢出保护
