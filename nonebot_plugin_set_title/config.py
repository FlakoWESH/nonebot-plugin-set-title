"""
set_title 插件配置（Alconna优化版）
"""
from pydantic import BaseModel


class SetTitleConfig(BaseModel):
    """群头衔管理插件配置"""

    # 批量修改头衔时每次API调用的间隔（秒），防止QQ风控
    set_title_batch_interval: float = 0.5

    # 批量功能是否仅允许群管理员使用
    set_title_batch_admin_only: bool = True

    # 头衔最大GBK字节数（QQ官方限制约6个汉字=12字节）
    set_title_max_gbk_length: int = 12

    # 单用户命令冷却时间（秒）
    set_title_cd: int = 10

    # 批量命令冷却时间（秒）
    set_title_batch_cd: int = 15
