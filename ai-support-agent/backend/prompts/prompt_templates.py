"""
prompts/prompt_templates.py — LLM Prompt Assembly Functions
============================================================

These pure functions assemble the final prompt strings that are sent to
the LLM. Separating prompt construction from service logic means:

  - Prompts are easy to review, test, and tune in one place.
  - Services stay clean — they call a builder, not string-concatenation code.
  - Template changes never require touching AgentService or LLMService.

Design note: these are pure functions because prompt building is a
deterministic, stateless text transformation. No class is needed.
"""


def build_order_prompt(
    system_prompt: str,
    tool_result: str,
    customer_message: str,
) -> str:
    """
    Construct the full LLM prompt for an order-status query.

    The prompt injects the live order data retrieved from SQLite so the
    LLM can compose an accurate, natural-language response without
    fabricating details.

    Args:
        system_prompt     (str): The agent's persona and behavioural rules.
        tool_result       (str): Formatted order string from OrderRepository.
        customer_message  (str): The original customer query.

    Returns:
        str: A fully assembled prompt ready to be sent to the LLM.
    """
    return f"""
[SYSTEM INSTRUCTIONS]
{system_prompt}

[ORDER DATA FROM DATABASE]
{tool_result}

[CUSTOMER MESSAGE]
{customer_message}
""".strip()


def build_rag_prompt(
    system_prompt: str,
    context_text: str,
    customer_message: str,
) -> str:
    """
    Construct the full LLM prompt for a general knowledge-base query.

    The prompt injects the most semantically relevant document chunks
    retrieved from ChromaDB so the LLM answers from factual context rather
    than hallucinating.

    Args:
        system_prompt    (str): The agent's persona and behavioural rules.
        context_text     (str): Concatenated document chunks from RAGService.
        customer_message (str): The original customer query.

    Returns:
        str: A fully assembled prompt ready to be sent to the LLM.
    """
    return f"""
[SYSTEM INSTRUCTIONS]
{system_prompt}

Please rely strictly on the facts provided in the [COMPANY KNOWLEDGE BASE CONTEXT] below to answer.
If the context does not contain the answer, politely state that you do not have that information and advise them to contact support@company.com.

[COMPANY KNOWLEDGE BASE CONTEXT]
{context_text}

[CUSTOMER MESSAGE]
{customer_message}
""".strip()
