from langchain_openai import ChatOpenAI
import base64

API_KEY = "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"

def load_image_base64(image_path):
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode()

# ✅ Use Google Gemini instead - more reliable and free
llm = ChatOpenAI(
    model="google/gemini-2.5-flash-image",  # Very reliable free option
    temperature=0.1,
    max_tokens=200,
    base_url="https://openrouter.ai/api/v1",
    api_key=API_KEY
)

image_path = r"C:\Users\raj\OneDrive\Desktop\Shiva_project\download4.jpeg"
image_b64 = load_image_base64(image_path)

question = "Is he wearing a tie?"

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