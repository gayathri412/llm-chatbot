from groq import Groq
import google.generativeai as genai

try:
    import vertexai
    from vertexai.generative_models import GenerativeModel as VertexGenerativeModel
except ImportError:
    vertexai = None
    VertexGenerativeModel = None

try:
    from tenacity import retry, stop_after_attempt, wait_exponential
except ImportError:
    def retry(*args, **kwargs):
        def decorator(func):
            return func
        return decorator

    def stop_after_attempt(*args, **kwargs):
        return None

    def wait_exponential(*args, **kwargs):
        return None

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args, **kwargs):
        return False

from app.secret_manager import get_secret_value
from app.config import get_settings
from app.token_budget import trim_to_token_budget


load_dotenv()

GROQ_API_KEY = get_secret_value("GROQ_API_KEY", "GROQ_API_KEY_SECRET")
GEMINI_API_KEY = get_secret_value("GEMINI_API_KEY", "GEMINI_API_KEY_SECRET")

groq_client = Groq(api_key=GROQ_API_KEY)
genai.configure(api_key=GEMINI_API_KEY)


@retry(wait=wait_exponential(multiplier=1, min=1, max=8), stop=stop_after_attempt(3), reraise=True)
def _call_groq(user_input: str, temperature: float = 0.2, max_output_tokens: int | None = None) -> str:
    settings = get_settings()
    request = {
        "model": settings.groq_llama_model,
        "messages": [{"role": "user", "content": user_input}],
        "temperature": temperature,
    }
    if max_output_tokens:
        request["max_completion_tokens"] = max_output_tokens

    try:
        response = groq_client.chat.completions.create(**request)
    except TypeError:
        request.pop("max_completion_tokens", None)
        response = groq_client.chat.completions.create(**request)

    return response.choices[0].message.content


@retry(wait=wait_exponential(multiplier=1, min=1, max=8), stop=stop_after_attempt(3), reraise=True)
def _call_gemini(user_input: str, temperature: float = 0.2, max_output_tokens: int | None = None) -> str:
    settings = get_settings()
    model = genai.GenerativeModel(settings.gemini_api_model)
    generation_config = {"temperature": temperature}
    if max_output_tokens:
        generation_config["max_output_tokens"] = max_output_tokens

    response = model.generate_content(
        user_input,
        generation_config=generation_config,
    )
    return response.text


@retry(wait=wait_exponential(multiplier=1, min=1, max=8), stop=stop_after_attempt(3), reraise=True)
def _call_vertex_gemini(
    user_input: str,
    temperature: float = 0.2,
    max_output_tokens: int | None = None,
) -> str:
    settings = get_settings()
    if vertexai is None or VertexGenerativeModel is None:
        raise RuntimeError("google-cloud-aiplatform is required for Vertex AI Gemini.")
    if not settings.vertex_ai_project_id:
        raise RuntimeError("VERTEX_AI_PROJECT_ID or GCP_PROJECT_ID is required for Vertex AI Gemini.")

    vertexai.init(project=settings.vertex_ai_project_id, location=settings.vertex_ai_location)
    model = VertexGenerativeModel(settings.vertex_ai_gemini_model)
    generation_config = {"temperature": temperature}
    if max_output_tokens:
        generation_config["max_output_tokens"] = max_output_tokens

    response = model.generate_content(user_input, generation_config=generation_config)
    return response.text


def chat_completion(
    messages,
    model_choice="Llama",
    temperature: float = 0.2,
    max_output_tokens: int | None = None,
    max_input_tokens: int | None = None,
):
    settings = get_settings()
    max_input_tokens = max_input_tokens or settings.max_input_tokens
    max_output_tokens = max_output_tokens or settings.max_output_tokens
    user_input = trim_to_token_budget(messages[-1]["content"], max_input_tokens).text

    try:
        if model_choice == "Gemini":
            if settings.llm_provider.lower() in {"vertex_gemini", "vertex", "vertex_ai", "vertex-ai"}:
                try:
                    return _call_vertex_gemini(
                        user_input,
                        temperature=temperature,
                        max_output_tokens=max_output_tokens,
                    )
                except Exception:
                    pass

            try:
                return _call_gemini(
                    user_input,
                    temperature=temperature,
                    max_output_tokens=max_output_tokens,
                )
            except Exception:
                return _call_groq(
                    user_input,
                    temperature=temperature,
                    max_output_tokens=max_output_tokens,
                )

        if model_choice == "Llama":
            return _call_groq(
                user_input,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
            )

        return "This is a fallback response."

    except Exception as e:
        return f"Error: {str(e)}"
