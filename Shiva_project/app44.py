from langchain_openai import ChatOpenAI
import base64
import time

def load_image_base64(image_path):
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode()

# Try these models one by one:

# Option 1: Google Gemini Flash (Usually reliable)
# llm = ChatOpenAI(
#     model="google/gemini-flash-1.5",
#     temperature=0.1,
#     max_tokens=300,
#     base_url="https://openrouter.ai/api/v1",
#     api_key="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"
# )

# Option 2: Meta Llama Vision
llm = ChatOpenAI(
    model="meta-llama/llama-3.2-11b-vision-instruct:free",
    temperature=0.1,
    max_tokens=300,
    base_url="https://openrouter.ai/api/v1",
    api_key="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"
)

# Option 3: Qwen 2 VL (7B - smaller, might be less rate-limited)
# llm = ChatOpenAI(
#     model="qwen/qwen2-vl-7b-instruct:free",
#     temperature=0.1,
#     max_tokens=300,
#     base_url="https://openrouter.ai/api/v1",
#     api_key="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"
# )

# Option 4: OpenAI GPT-4o Mini (Very small cost, ~$0.000425 per request)
# llm = ChatOpenAI(
#     model="openai/gpt-4o-mini",
#     temperature=0.1,
#     max_tokens=300,
#     base_url="https://openrouter.ai/api/v1",
#     api_key="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"
# )

image_path = r"C:\Users\raj\OneDrive\Desktop\Shiva_project\download4.jpeg"
image_b64 = load_image_base64(image_path)

question = "Is he wearing a tie?"

# Retry logic
max_retries = 3
retry_delay = 5

for attempt in range(max_retries):
    try:
        response = llm.invoke([
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": question},  
                    {
                        "type": "image_url",  
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_b64}"
                        }
                    }
                ]
            }
        ])
        print("Answer:", response.content)
        break
    except Exception as e:
        if "429" in str(e) and attempt < max_retries - 1:
            print(f"Rate limited. Retrying in {retry_delay} seconds... (Attempt {attempt + 1}/{max_retries})")
            time.sleep(retry_delay)
            retry_delay *= 2
        else:
            print(f"Error: {e}")
            break