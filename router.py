"""All active chat interfaces use the V2 command engine."""
from agent_v2.service import handle_request


def route_request(user_input, context_id="default", *, request_id=None, actor_name=""):
    from pending import get_pending_action, clear_pending_action
    old = get_pending_action(context_id)
    if old:
        clear_pending_action(context_id)
        if user_input.strip() in {"取消", "算了", "不用改了", "不修改了"}:
            return "已经取消这次修改。"
        return "检测到旧版待确认请求，已取消且没有写入。请重新提出修改请求，新版会显示预览。"
    return handle_request(user_input, context_id, request_id=request_id, actor_name=actor_name)
