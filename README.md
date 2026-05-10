# FOC PI参数整定工具

基于Web的FOC（磁场定向控制）电机PI参数整定辅助工具，支持PMSM（永磁同步电机）的电流环和速度环PI参数整定。

## 功能特性

- **离线PI参数整定** - 支持带宽法、极点配置法、Ziegler-Nichols法三种整定算法
- **AI智能调参** - 集成DeepSeek大模型，提供专业的调参建议和故障诊断
- **实时参数计算** - 输入电机参数即可获得完整的PI参数和性能预估
- **可视化展示** - 公式渲染、代码示例、调参指导一体化展示

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置API密钥

编辑 `config/ai_config.yaml`，填入你的DeepSeek API密钥：

```yaml
ai:
  provider: deepseek
  api_key: sk-your-api-key-here
  base_url: https://api.deepseek.com/v1
  model: deepseek-v4-flash
```

### 启动服务

```bash
python3 -c "
import uvicorn
from src.web.app import app
uvicorn.run(app, host='0.0.0.0', port=8000)
"
```

访问 http://localhost:8000 即可使用。

## 项目结构

```
motor_para/
├── src/
│   ├── core/               # 核心算法层
│   │   ├── models.py       # 数据模型定义
│   │   ├── tuner.py        # 主整定器
│   │   ├── validator.py    # 参数验证
│   │   └── algorithms/     # 整定算法实现
│   ├── ai/                 # AI集成层
│   │   ├── engine.py       # AI决策引擎
│   │   └── providers/      # API适配
│   └── web/                # Web服务层
│       ├── app.py          # FastAPI应用
│       ├── routes/         # API路由
│       └── static/         # 前端静态文件
├── config/                 # 配置文件
├── tests/                  # 测试
├── requirements.txt        # 依赖列表
└── CLAUDE.md              # 项目文档
```

## 整定算法

### 带宽法（Bandwidth）

```
电流环: Kp = ωc × L,  Ki = ωc × R
速度环: Kp = 2ζωnJ/Kt, Ki = ωn²J/Kt
```

### 极点配置法（Pole Placement）

```
电流环: Kp = 2 × pole × L - R, Ki = pole² × L
速度环: Kp = J(p1 + p2)/Kt, Ki = J·p1·p2/Kt
```

### Ziegler-Nichols法

```
电流环: τ = L/R, Kp = 0.9R, Ki = Kp/(3.33τ)
速度环: τeq = 1/ωc, Kp = J/(Kt·τeq), Ki = Kp/(2τeq)
```

## API接口

### 整定API

```http
POST /api/tune
Content-Type: application/json

{
  "motor_params": {
    "Rs": 0.5,
    "Ld": 0.001,
    "Lq": 0.001,
    "Psi_f": 0.1,
    "J": 0.001,
    "p": 4
  },
  "method": "auto",
  "damping": 0.707
}
```

### AI聊天API

```http
POST /api/chat
Content-Type: application/json

{
  "message": "电流环振荡怎么办？"
}
```

## 技术栈

- **后端**: Python 3.10+, FastAPI, Pydantic
- **前端**: HTML5, Tailwind CSS, Alpine.js
- **AI**: OpenAI API (DeepSeek)
- **可视化**: KaTeX (公式渲染), Highlight.js (代码高亮)

## 开发规范

- 使用Black格式化，行宽88
- 使用类型注解（Type Hints）
- 函数和类必须有docstring
- 变量命名：snake_case
- 类命名：PascalCase

## 许可证

MIT License
