from groq import Groq
import google.generativeai as genai

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


load_dotenv()

GROQ_API_KEY = get_secret_value("GROQ_API_KEY", "GROQ_API_KEY_SECRET")
GEMINI_API_KEY = get_secret_value("GEMINI_API_KEY", "GEMINI_API_KEY_SECRET")

groq_client = Groq(api_key=GROQ_API_KEY)
genai.configure(api_key=GEMINI_API_KEY)


@retry(wait=wait_exponential(multiplier=1, min=1, max=8), stop=stop_after_attempt(3), reraise=True)
def _call_groq(user_input: str, temperature: float = 0.2) -> str:
    response = groq_client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": user_input}],
        temperature=temperature,
    )
    return response.choices[0].message.content


@retry(wait=wait_exponential(multiplier=1, min=1, max=8), stop=stop_after_attempt(3), reraise=True)
def _call_gemini(user_input: str, temperature: float = 0.2) -> str:
    model = genai.GenerativeModel("gemini-2.5-flash")
    response = model.generate_content(
        user_input,
        generation_config={"temperature": temperature},
    )
    return response.text


def chat_completion(messages, model_choice="Llama", temperature: float = 0.2):
    user_input = messages[-1]["content"]

    try:
        if model_choice == "Gemini":
            try:
                return _call_gemini(user_input, temperature=temperature)
            except Exception:
                return _call_groq(user_input, temperature=temperature)

        if model_choice == "Llama":
            return _call_groq(user_input, temperature=temperature)

        return "This is a fallback response."

    except Exception as e:
        return f"Error: {str(e)}"
