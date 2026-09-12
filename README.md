# nonebot-plugin-set-title

NoneBot2 群头衔管理插件，支持单用户设置和批量设置 QQ 群专属头衔。

## 功能特性

- **单用户设置头衔**：快速修改自己或指定群成员的专属头衔
- **批量设置头衔**：一次@多名成员，批量设置相同头衔，自动限流防风控
- **权限校验**：机器人需为群主（QQ官方接口硬性限制），修改他人头衔需管理员
- **头衔长度校验**：自动检测 GBK 字节数，防止超长头衔被QQ拒绝
- **冷却限流**：单用户命令和批量命令分别设置冷却时间，防止滥用
- **Alconna 优化**：使用 Alconna 命令解析器，类型安全参数获取，支持自动生成帮助信息

## 安装

### 使用 nb-cli（推荐）

```bash
nb plugin install nonebot-plugin-set-title
```

### 使用 pip

```bash
pip install nonebot-plugin-set-title
```

然后在 `pyproject.toml` 中添加：

```toml
[tool.nonebot]
plugins = ["nonebot_plugin_set_title"]
```

## 使用方法

### 单用户设置头衔

```
qst <头衔内容>          # 修改自己的头衔
qst <头衔内容> @用户    # 修改指定用户的头衔
```

示例：
```
qst 已登记
qst 管理员 @123456
```

### 批量设置头衔

```
批量设置头衔 <头衔内容> @用户1 @用户2 @用户3
```

别名：`批量改头衔`、`批量设置群头衔`

示例：
```
批量设置头衔 已登记 @用户1 @用户2 @用户3
```

## 配置项

在 `.env` 文件中添加以下配置（均为可选，有默认值）：

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `SET_TITLE_BATCH_INTERVAL` | float | 0.5 | 批量修改时每次API调用间隔（秒），防止QQ风控 |
| `SET_TITLE_BATCH_ADMIN_ONLY` | bool | true | 批量功能是否仅允许群管理员使用 |
| `SET_TITLE_MAX_GBK_LENGTH` | int | 12 | 头衔最大GBK字节数（约6个汉字） |
| `SET_TITLE_CD` | int | 10 | 单用户命令冷却时间（秒） |
| `SET_TITLE_BATCH_CD` | int | 15 | 批量命令冷却时间（秒） |

## 注意事项

1. **机器人必须为群主**：QQ官方接口 `set_group_special_title` 要求调用者为群主，否则会失败
2. **头衔长度限制**：QQ官方限制头衔最多约6个汉字（12字节GBK），超长会被拒绝
3. **批量限流**：批量设置几十人不会触发风控；若需批量上百人，建议调大 `SET_TITLE_BATCH_INTERVAL`
4. **协议端兼容**：基于 OneBot v11 标准API开发，适配 go-cqhttp、NapCatQQ、Lagrange.Core 等主流协议端

## 依赖

- nonebot2 >= 2.0.0
- nonebot-adapter-onebot >= 2.0.0
- nonebot-plugin-alconna >= 0.50.0

## 许可证

MIT
