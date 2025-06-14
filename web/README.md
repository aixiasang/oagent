# AI 聊天机器人 Web 界面

基于 Flask 的 AI 聊天机器人 Web 界面，支持流式输出和现代化的用户体验。

## 功能特性

- 🚀 **流式输出**: 实时显示 AI 回复，提供流畅的对话体验
- 🎨 **现代化界面**: 响应式设计，支持桌面和移动设备
- 🧠 **推理显示**: 显示 AI 的推理过程（reasoning_content）
- 💬 **对话管理**: 支持清空对话历史
- ⚡ **实时交互**: 基于 Server-Sent Events (SSE) 的实时通信
- 🔧 **易于部署**: 简单的 Flask 应用，易于部署和维护

## 项目结构

```
web/
├── app.py                 # Flask 主应用
├── templates/
│   └── chat.html         # 聊天界面模板
├── requirements.txt      # Python 依赖
└── README.md            # 说明文档
```

## 安装和运行

### 1. 安装依赖

```bash
cd web
pip install -r requirements.txt
```

### 2. 运行应用

```bash
python app.py
```

应用将在 `http://localhost:5000` 启动。

### 3. 访问界面

打开浏览器访问 `http://localhost:5000` 即可使用聊天界面。

## API 接口

### POST /chat

发送聊天消息，返回流式响应。

**请求体:**
```json
{
    "message": "你好"
}
```

**响应:** Server-Sent Events 流

```
data: {"type": "reasoning", "content": "推理内容..."}
data: {"type": "content", "content": "回复内容..."}
data: {"type": "end"}
```

### POST /clear

清空聊天历史。

**响应:**
```json
{
    "success": true,
    "message": "聊天历史已清空"
}
```

### GET /health

健康检查接口。

**响应:**
```json
{
    "status": "healthy",
    "agent_initialized": true
}
```

## 技术实现

### 流式输出

使用 Flask 的 `Response` 对象和 Server-Sent Events (SSE) 实现流式输出：

1. 前端使用 `fetch` API 读取流式响应
2. 后端使用 `yield` 生成器逐步发送数据
3. 支持推理内容和主要内容的分别显示

### 消息处理

- 使用 `agent.fn_chat()` 方法处理用户消息
- 通过回调函数捕获流式输出
- 区分 `reasoning_content` 和 `content` 两种类型的内容

### 前端特性

- **响应式设计**: 适配不同屏幕尺寸
- **实时输入**: 支持 Enter 发送，Shift+Enter 换行
- **自动滚动**: 新消息自动滚动到底部
- **输入状态管理**: 发送时禁用输入，防止重复提交
- **错误处理**: 友好的错误提示和重试机制

## 配置说明

应用会自动从父目录导入 Agent 配置：

```python
from config import get_siliconflow_model
from agent.agent import Agent
```

如果配置失败，会使用默认配置初始化 Agent。

## 部署建议

### 开发环境

```bash
python app.py
```

### 生产环境

使用 Gunicorn 部署：

```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Docker 部署

可以创建 Dockerfile 进行容器化部署：

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 5000

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
```

## 故障排除

### 常见问题

1. **Agent 初始化失败**
   - 检查配置文件是否正确
   - 确保所有依赖模块可以正常导入

2. **流式输出不工作**
   - 检查浏览器是否支持 Server-Sent Events
   - 确保网络连接稳定

3. **界面显示异常**
   - 检查模板文件是否完整
   - 清除浏览器缓存

### 日志查看

应用会在控制台输出详细的日志信息，包括：
- Agent 初始化状态
- 请求处理过程
- 错误信息

## 扩展功能

可以考虑添加的功能：

- 用户认证和会话管理
- 对话历史持久化
- 多模型切换
- 文件上传支持
- 语音输入/输出
- 主题切换
- 导出对话记录

## 许可证

本项目遵循 MIT 许可证。