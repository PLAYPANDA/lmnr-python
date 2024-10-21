from enum import Enum
from opentelemetry.semconv_ai import SpanAttributes

SPAN_INPUT = "lmnr.span.input"
SPAN_OUTPUT = "lmnr.span.output"
SPAN_TYPE = "lmnr.span.type"
SPAN_PATH = "lmnr.span.path"

ASSOCIATION_PROPERTIES = "lmnr.association.properties"
SESSION_ID = "session_id"
USER_ID = "user_id"
TRACE_TYPE = "trace_type"


# exposed to the user, configurable
class Attributes(Enum):
    # not SpanAttributes.LLM_USAGE_PROMPT_TOKENS,
    INPUT_TOKEN_COUNT = "gen_ai.usage.input_tokens"
    # not SpanAttributes.LLM_USAGE_COMPLETION_TOKENS,
    OUTPUT_TOKEN_COUNT = "gen_ai.usage.output_tokens"
    PROVIDER = SpanAttributes.LLM_SYSTEM
    REQUEST_MODEL = SpanAttributes.LLM_REQUEST_MODEL
    RESPONSE_MODEL = SpanAttributes.LLM_RESPONSE_MODEL
