import os

from openai import AsyncOpenAI


def evaluate_window(trades: list[dict]) -> float:
    returns: list[float] = []

    for trade in trades:
        entry = float(trade["entry"])
        exit_price = float(trade["exit"])
        side = str(trade["side"]).lower()

        if entry == 0:
            continue

        if side == "long":
            trade_return = (exit_price - entry) / entry
        elif side == "short":
            trade_return = (entry - exit_price) / entry
        else:
            continue

        returns.append(trade_return)

    if not returns:
        return 0.0

    average_return = sum(returns) / len(returns)
    return max(-1.0, min(1.0, average_return))


def _strip_markdown_code_blocks(text: str) -> str:
    stripped = text.strip()

    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()

    return stripped.replace("```", "").strip()


async def mutate_prompt(current_prompt: str, score: float, market_context: str) -> str:
    META_PROMPT = (
        f"你是一个交易优化器。智能体使用了这个提示词：{current_prompt}。"
        f"在以下市场环境中：{market_context}，它获得了 {score} 的评分。"
        "请重写提示词以修复缺陷并改进风控。只输出纯文本的新提示词。"
    )

    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": META_PROMPT}],
    )

    content = response.choices[0].message.content or ""
    return _strip_markdown_code_blocks(content)
