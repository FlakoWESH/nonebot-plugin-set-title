"""
群头衔管理插件（Alconna优化版）
功能：单用户设置头衔 + 批量设置头衔
优化点：
- 使用 Alconna 命令解析器替代手动遍历 MessageSegment
- 使用 UniMessage 统一消息发送，跨平台兼容
- 使用 Arparma 解析结果，类型安全的参数获取
- 使用 At/Text 消息段类型，替代字符串类型判断
依赖：nonebot2 + nonebot-adapter-onebot + nonebot-plugin-alconna
"""
import asyncio
import time
from typing import Dict, List, Tuple

from arclet.alconna import Alconna, Args
from nonebot import get_plugin_config
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent
from nonebot.log import logger
from nonebot.plugin import PluginMetadata
from nonebot_plugin_alconna import (
    AlconnaMatches,
    Arparma,
    At,
    Text,
    UniMessage,
    on_alconna,
)

from .config import SetTitleConfig

# ========== 插件元数据 ==========
__plugin_meta__ = PluginMetadata(
    name="群头衔管理",
    description="单用户/批量设置QQ群专属头衔，需机器人为群主（Alconna优化版）",
    usage=(
        "qst <头衔> - 修改自己的头衔\n"
        "qst <头衔> @用户 - 修改指定用户的头衔\n"
        "批量设置头衔 <头衔> @多个用户 - 批量设置多名成员的头衔"
    ),
    type="application",
    homepage="https://github.com/nonebot/plugin-alconna",
    supported_adapters={"~onebot.v11"},
)

# ========== 加载配置 ==========
config = get_plugin_config(SetTitleConfig)

# ========== 简易限流（内存实现） ==========
_last_called: Dict[str, float] = {}


def _check_cd(key: str, cd_seconds: int) -> Tuple[bool, float]:
    """检查冷却时间，返回(是否允许, 剩余秒数)"""
    now = time.time()
    if key in _last_called:
        elapsed = now - _last_called[key]
        if elapsed < cd_seconds:
            return False, cd_seconds - elapsed
    _last_called[key] = now
    return True, 0.0


# ========== 权限校验工具（原生OneBot API） ==========
async def _is_group_owner(bot: Bot, group_id: int, user_id: int) -> bool:
    """检查用户是否为群群主"""
    try:
        info = await bot.get_group_member_info(group_id=group_id, user_id=user_id)
        return info.get("role") == "owner"
    except Exception as e:
        logger.warning(f"获取群成员信息失败 group={group_id} user={user_id}: {e}")
        return False


async def _is_group_admin(bot: Bot, group_id: int, user_id: int) -> bool:
    """检查用户是否为群管理员或群主"""
    try:
        info = await bot.get_group_member_info(group_id=group_id, user_id=user_id)
        return info.get("role") in ("owner", "admin")
    except Exception as e:
        logger.warning(f"获取群成员信息失败 group={group_id} user={user_id}: {e}")
        return False


# ========== Alconna参数解析工具 ==========
def _parse_content(content: UniMessage) -> Tuple[List[int], str]:
    """从UniMessage中解析@用户列表和头衔文本

    Alconna优化点：使用 isinstance(seg, At) / isinstance(seg, Text)
    替代原生的 seg.type == "at" / seg.type == "text" 字符串判断，
    类型更安全，跨平台兼容性更好。

    参数:
        content: Alconna解析后的UniMessage消息内容

    返回:
        (at用户ID列表, 头衔文本)
    """
    at_users: List[int] = []
    title_parts: List[str] = []

    for seg in content:
        if isinstance(seg, At):
            # At.target 是字符串类型的用户QQ号
            # 过滤@全体成员（flag != "user"）
            if seg.flag == "user" and seg.target and seg.target != "all":
                at_users.append(int(seg.target))
        elif isinstance(seg, Text):
            # Text.text 是文本内容
            text = seg.text.strip()
            if text:
                title_parts.append(text)

    return at_users, " ".join(title_parts).strip()


def _check_title_length(title: str) -> str | None:
    """校验头衔长度，返回错误信息（None表示通过）"""
    try:
        if len(title.encode("gbk")) > config.set_title_max_gbk_length:
            return "头衔过长，请缩短后重试（最多6个汉字）"
    except UnicodeEncodeError:
        return "头衔包含不支持的字符"
    return None


# ========== 命令1：单用户设置头衔 ==========
# Alconna优化点：
# - 使用 Alconna("qst", Args["content", UniMessage, ""]) 定义命令
# - content 参数接收整个消息内容（包含@用户和文本），默认值为空UniMessage
# - on_alconna 自动处理命令匹配、别名、参数解析
qst_cmd = on_alconna(
    Alconna("qst", Args["content", UniMessage, ""]),
    priority=5,
    block=True,
)


@qst_cmd.handle()
async def set_title_handler(
    bot: Bot,
    event: GroupMessageEvent,
    arp: Arparma = AlconnaMatches(),
):
    """单用户设置头衔处理函数

    Alconna优化点：
    - 使用 Arparma = AlconnaMatches() 依赖注入获取解析结果
    - 使用 arp.query[UniMessage]("content") 类型安全地获取参数
    - 替代原生的 args: Message = CommandArg() + 手动遍历seg
    """
    # 限流检查
    cd_key = f"qst:{event.user_id}"
    allowed, remain = _check_cd(cd_key, config.set_title_cd)
    if not allowed:
        await UniMessage.text(f"操作太频繁啦，{remain:.0f}秒后再试吧~").finish()

    # 校验机器人群主身份
    if not await _is_group_owner(bot, event.group_id, int(bot.self_id)):
        await UniMessage.text("机器人不是群主，无法设置群头衔").finish()

    # Alconna参数解析：类型安全地获取content参数
    content = arp.query[UniMessage]("content", UniMessage())
    at_users, title = _parse_content(content)
    target_user = at_users[0] if at_users else event.user_id

    if not title:
        await UniMessage.text("请输入要设置的头衔内容\n用法：qst <头衔> [@用户]").finish()

    # 头衔长度校验
    if err := _check_title_length(title):
        await UniMessage.text(err).finish()

    # 权限校验：修改他人头衔需管理员
    if target_user != event.user_id:
        if not await _is_group_admin(bot, event.group_id, event.user_id):
            await UniMessage.text("仅管理员可修改他人头衔").finish()

    # 调用OneBot API设置头衔
    try:
        await bot.set_group_special_title(
            group_id=event.group_id,
            user_id=target_user,
            special_title=title,
            duration=-1,
        )
        logger.info(f"设置头衔成功 group={event.group_id} user={target_user} title={title}")
        await UniMessage.text("头衔设置成功").finish()
    except Exception as e:
        logger.error(f"设置头衔失败 group={event.group_id} user={target_user}: {e}")
        await UniMessage.text(f"设置失败：{str(e)}").finish()


# ========== 命令2：批量设置头衔 ==========
# Alconna优化点：
# - 使用 aliases 参数注册命令别名，替代原生的 on_command(aliases={...})
# - Args["content", UniMessage, ""] 接收包含多个@用户的完整消息
batch_cmd = on_alconna(
    Alconna("批量设置头衔", Args["content", UniMessage, ""]),
    aliases={"批量改头衔", "批量设置群头衔"},
    priority=5,
    block=True,
)


@batch_cmd.handle()
async def batch_set_title_handler(
    bot: Bot,
    event: GroupMessageEvent,
    arp: Arparma = AlconnaMatches(),
):
    """批量设置头衔处理函数"""
    # 限流检查（群级限流）
    cd_key = f"batch:{event.group_id}"
    allowed, remain = _check_cd(cd_key, config.set_title_batch_cd)
    if not allowed:
        await UniMessage.text(f"群内批量操作冷却中，{remain:.0f}秒后再试吧~").finish()

    # 1. 校验机器人群主身份
    if not await _is_group_owner(bot, event.group_id, int(bot.self_id)):
        await UniMessage.text("机器人不是群主，无法设置群头衔").finish()

    # 2. 发送者权限校验
    if config.set_title_batch_admin_only:
        if not await _is_group_admin(bot, event.group_id, event.user_id):
            await UniMessage.text("仅群管理员可使用批量设置功能").finish()

    # 3. Alconna参数解析
    content = arp.query[UniMessage]("content", UniMessage())
    at_users, title = _parse_content(content)

    if not at_users:
        await UniMessage.text(
            "请@需要设置头衔的群成员\n用法：批量设置头衔 <头衔> @用户1 @用户2"
        ).finish()
    if not title:
        await UniMessage.text("请输入要设置的头衔内容").finish()

    # 头衔长度校验
    if err := _check_title_length(title):
        await UniMessage.text(err).finish()

    logger.info(
        f"批量设置头衔开始 group={event.group_id} count={len(at_users)} title={title}"
    )

    # 4. 批量执行（串行+间隔限流）
    success_count = 0
    failed_list: List[Tuple[int, str]] = []

    for user_id in at_users:
        try:
            await bot.set_group_special_title(
                group_id=event.group_id,
                user_id=user_id,
                special_title=title,
                duration=-1,
            )
            success_count += 1
        except Exception as e:
            err_msg = "接口调用失败"
            if "ActionFailed" in str(e):
                err_msg = "调用失败（可能用户不存在或头衔违规）"
            failed_list.append((user_id, err_msg))
            logger.warning(f"设置头衔失败 group={event.group_id} user={user_id}: {e}")

        await asyncio.sleep(config.set_title_batch_interval)

    # 5. 结果汇总（使用UniMessage构建多行文本）
    result = UniMessage.text(f"批量头衔设置完成\n成功：{success_count} 人")
    if failed_list:
        result += UniMessage.text(f"\n失败：{len(failed_list)} 人")
        if len(failed_list) <= 5:
            for uid, reason in failed_list:
                result += UniMessage.text(f"\n· {uid}：{reason}")
        else:
            result += UniMessage.text("\n（失败人数较多，请检查头衔内容是否合规）")

    logger.info(
        f"批量设置头衔完成 group={event.group_id} success={success_count} failed={len(failed_list)}"
    )
    await result.finish()
