import copy
import hashlib
import sqlite3

from agent_v2.engine import execute, handle_pending
from agent_v2.parser import parse_command, ParseError
from agent_v2.schema import Command
from agent_v2.store import Repository


def default_repository():
    import baby
    return Repository(baby.DATA_FILE, baby.EXAMPLE_DATA_FILE)


def receipt_key(context_id, request_id):
    return hashlib.sha256((context_id + "\0" + request_id).encode()).hexdigest() if request_id else None


def finish(data, context_id, text, answer, key=None):
    state = data["_agent_v2"]
    ctx = state["contexts"].setdefault(context_id, {})
    ctx["generation"] = ctx.get("generation", 0) + 1
    history = ctx.setdefault("history", [])
    history.extend([{"role": "user", "content": text[:2000]}, {"role": "assistant", "content": answer[:4000]}])
    ctx["history"] = history[-6:]
    if key:
        state["receipts"][key] = {"text": text, "answer": answer}
    return answer


def existing_receipt(data, key, text):
    record = data["_agent_v2"]["receipts"].get(key) if key else None
    if record:
        return record["answer"] if record["text"] == text else "消息编号重复但内容不同，本次未执行。"
    return None


def handle_request(text, context_id="default", *, request_id=None, actor_name="", repository=None, parser=None):
    text = str(text).strip()
    context_id = str(context_id or "default")
    if not text or len(text) > 6000:
        return "请输入1到6000字的一条请求。"
    repository = repository or default_repository()
    parser = parser or parse_command
    key = receipt_key(context_id, str(request_id)) if request_id else None
    try:
        with repository.transaction() as data:
            cached = existing_receipt(data, key, text)
            if cached is not None:
                return cached
            state = data["_agent_v2"]
            ctx = state["contexts"].setdefault(context_id, {})
            answer = handle_pending(data, state, ctx, context_id, text, actor_name)
            if answer is not None:
                return finish(data, context_id, text, answer, key)
            context = copy.deepcopy(ctx)
            generation = ctx.get("generation", 0)
        try:
            command = parser(text, context)
            if not isinstance(command, Command):
                command = Command.model_validate(command)
        except Exception as exc:
            if isinstance(exc, ParseError):
                return f"{exc}。没有新增或修改任何记录。"
            return "指令未通过安全校验，没有新增或修改任何记录。请明确记录名称和内容。"
        with repository.transaction() as data:
            cached = existing_receipt(data, key, text)
            if cached is not None:
                return cached
            ctx = data["_agent_v2"]["contexts"].setdefault(context_id, {})
            if ctx.get("generation", 0) != generation:
                return "本会话刚有另一条请求完成，请重新发送这条消息，以免引用过时的记录。"
            if command.action == "UNKNOWN":
                result = "我还无法安全确定这次需求。请一次说明一条记录及新增、查询或修改内容；本次没有写入。"
            elif command.action == "KNOWLEDGE":
                result = {"records": []}
            else:
                result = execute(data, command, context_id, actor_name)
            if isinstance(result, str):
                return finish(data, context_id, text, result, key)
            selected_records = result["records"]
        try:
            from agent_v2.knowledge import evidence_answer
            answer = evidence_answer(text, selected_records)
        except Exception:
            answer = "知识服务暂时不可用，请稍后重试。宝宝记录未被修改。"
        with repository.transaction() as data:
            cached = existing_receipt(data, key, text)
            if cached is not None:
                return cached
            ctx = data["_agent_v2"]["contexts"].setdefault(context_id, {})
            if ctx.get("generation", 0) != generation:
                return answer + "\n（期间会话已更新，本回答未覆盖新上下文。）"
            return finish(data, context_id, text, answer, key)
    except (OSError, ValueError, sqlite3.Error) as exc:
        return "数据文件读取或保存失败。请停止写入并检查数据备份；不要重复确认。" + f"（{type(exc).__name__}）"
