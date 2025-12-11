## 系统概述
这是一个具有美观界面的联系人地址簿系统，支持联系人管理、分组、头像上传、导入导出等功能。

## 主要功能

### 1. **核心功能**
- ✅ 联系人增删改查
- ✅ 分组管理（家人、同事、朋友、同学等）
- ✅ 收藏功能（星标标记）
- ✅ 头像上传和显示
- ✅ 多种联系方式（电话、邮箱、微信、QQ、地址）

### 2. **特色功能**
- ✅ 中文拼音首字母提取（用于排序）
- ✅ Excel 导入/导出
- ✅ 响应式设计，支持移动端
- ✅ 美观的 UI 界面
- ✅ 动画效果和交互反馈

### 3. **技术特点**
- **后端**: Flask + SQLAlchemy + SQLite
- **前端**: HTML + CSS + JavaScript（内联）
- **文件处理**: 支持图片上传
- **数据处理**: Pandas 用于 Excel 操作

## 数据库设计

### 1. **Contact 表**
```python
id: Integer (主键)
name: String (姓名)
is_bookmarked: Boolean (是否收藏)
group: String (分组)
photo_path: String (头像路径)
first_letter: String (姓名首字母)
```

### 2. **ContactMethod 表**
```python
id: Integer (主键)
method_type: String (联系方式类型)
value: String (联系方式值)
contact_id: Integer (外键)
```

## 路由设计

| 路由 | 方法 | 功能 |
|------|------|------|
| `/` | GET | 显示所有联系人 |
| `/add` | GET/POST | 添加联系人 |
| `/edit/<id>` | GET/POST | 编辑联系人 |
| `/delete/<id>` | POST | 删除联系人 |
| `/bookmark/<id>` | POST | 切换收藏状态 |
| `/export` | GET | 导出为 Excel |
| `/import` | POST | 从 Excel 导入 |

## 运行说明

### 安装依赖
```bash
pip install flask flask-sqlalchemy pandas openpyxl
```

### 运行应用
```bash
python software.py
```

### 访问地址
```
http://127.0.0.1:5000
```

## 文件结构
```
项目根目录/
├── software.py          # 主程序文件
├── address_book.db      # 数据库文件（运行后生成）
├── static/
│   └── avatars/         # 头像存储目录
└── .gitignore           # Git 忽略文件
```

## 界面特点
1. **现代化设计**: 使用渐变背景、阴影效果、圆角设计
2. **响应式布局**: 适配不同屏幕尺寸
3. **交互反馈**: 动画效果、提示信息、确认对话框
4. **图标支持**: Font Awesome 图标库
5. **色彩系统**: 定义了一套完整的配色方案

## 待改进点（建议）
1. **安全性**: 当前使用硬编码的 `SECRET_KEY`
2. **文件上传**: 未限制文件类型和大小验证
3. **错误处理**: 需要更完善的异常处理
4. **代码结构**: 可以考虑将 HTML 模板分离到单独文件
5. **测试**: 添加单元测试和集成测试

## 使用场景
- 个人联系人管理
- 小型团队通讯录
- 客户关系管理（简化版）
- 教学示例项目

这是一个功能完善、界面美观的 Web 应用，适合作为学习项目或小型实际应用。
