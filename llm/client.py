import os
from dotenv import load_dotenv
from groq import Groq
import google.generativeai as genai

# Load .env
load_dotenv()

# 🔑 Load API keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Clients
groq_client = Groq(api_key=GROQ_API_KEY)
genai.configure(api_key=GEMINI_API_KEY)


def chat_completion(messages, model_choice="Llama"):
    user_input = messages[-1]["content"]

    try:
        # 🟢 GEMINI (with fallback to Llama)
        if model_choice == "Gemini":
            try:
                model = genai.GenerativeModel("gemini-1.5-flash")
                response = model.generate_content(user_input)
                return response.text
            except Exception:
                # fallback to Llama
                response = groq_client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[{"role": "user", "content": user_input}]
                )
                return response.choices[0].message.content

        # 🟢 LLAMA (GROQ)
        elif model_choice == "Llama":
            response = groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": user_input}]
            )
            return response.choices[0].message.content

        # 🟡 FALLBACK
        else:
            return "This is a fallback response."

    except Exception as e:
        return f"Error: {str(e)}"