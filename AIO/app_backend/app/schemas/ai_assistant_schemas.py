from pydantic import BaseModel, Field


class AiChatMessage(BaseModel):
    """One turn in the conversation. The frontend keeps the full history
    client-side and resends it each call — deliberately no server-side
    conversation storage: these chats are short-lived and don't need to
    survive an app restart, so a whole extra table (and its cleanup job)
    isn't worth it here."""
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str


class AiChatRequest(BaseModel):
    mode: str = Field(..., pattern="^(question|order)$")
    messages: list[AiChatMessage] = Field(..., min_length=1, max_length=40)


class AiChoiceOption(BaseModel):
    option_id: str
    label: str
    detail: str | None = None


class AiCartAddition(BaseModel):
    product_id: str
    name: str
    shop_name: str
    quantity: int
    price: float


class AiChatResponse(BaseModel):
    reply: str
    # Present when the assistant needs the user to pick between concrete
    # options (which store, which size, which weight) rather than guessing —
    # see present_choices in ai_assistant_service.py. The frontend renders
    # these as tappable chips instead of asking the user to type a choice
    # out in free text.
    choices: list[AiChoiceOption] | None = None
    # Items actually added to the cart during this turn (could be several,
    # for a multi-item order request) — lets the UI show a concrete
    # confirmation and refresh the cart badge.
    cart_additions: list[AiCartAddition] = []