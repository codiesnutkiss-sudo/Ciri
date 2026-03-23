from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx
import time
import urllib.parse
import os

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Auto-Locate index.html
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HTML_PATH = os.path.join(BASE_DIR, "static", "index.html") if os.path.exists(os.path.join(BASE_DIR, "static", "index.html")) else os.path.join(BASE_DIR, "index.html")

@app.get("/")
async def root():
    if os.path.exists(HTML_PATH):
        return FileResponse(HTML_PATH)
    return JSONResponse(content={"Error": "index.html not found"}, status_code=404)

# BROWSER DISGUISE (Bypasses Cloudflare Blocks)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*"
}

# --- 100% FREE DIRECT APIs ---

async def fetch_pollinations(prompt: str, model: str):
    """Direct text endpoint. Unblocked and incredibly fast."""
    encoded = urllib.parse.quote(prompt)
    url = f"https://text.pollinations.ai/prompt/{encoded}?model={model}"
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url, headers=HEADERS)
        if resp.status_code == 200:
            return resp.text
        raise Exception(f"Pollinations HTTP {resp.status_code}")

async def fetch_airforce(messages: list, model: str):
    """OpenAI-compatible free endpoint. Supports Vision and advanced models."""
    url = "https://api.airforce/v1/chat/completions"
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": 2000
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, json=payload, headers=HEADERS)
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"]
        raise Exception(f"Airforce HTTP {resp.status_code}")

# --- MAIN LOGIC ---

@app.post("/chat")
async def chat_endpoint(request: Request):
    try:
        data = await request.json()
        text = data.get("message")
        model_choice = data.get("model")
        image_data = data.get("image")
        
        start_time = time.time()
        ai_reply = ""

        # ==========================================
        # 1. LIVE VISION MODE (Images Attached)
        # ==========================================
        if image_data:
            try:
                messages = [{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": text + "\n[System: Analyze this attached image/screen carefully.]"},
                        {"type": "image_url", "image_url": {"url": image_data}}
                    ]
                }]
                # Use GPT-4o-Mini Vision capability on the free Airforce API
                ai_reply = await fetch_airforce(messages, "gpt-4o-mini")
            except Exception as e:
                ai_reply = f"Vision Error: The free vision endpoint dropped the request. Please try again. (Log: {str(e)})"

        # ==========================================
        # 2. TEXT MODE (No Images)
        # ==========================================
        else:
            try:
                if model_choice == "gpt-4":
                    # Uses GPT-4o via Pollinations
                    ai_reply = await fetch_pollinations(text, "openai")
                
                elif model_choice == "llama":
                    # Uses Llama 3 via Pollinations
                    ai_reply = await fetch_pollinations(text, "llama")
                
                elif model_choice == "deepseek":
                    # Uses DeepSeek via Airforce
                    ai_reply = await fetch_airforce([{"role": "user", "content": text}], "deepseek-coder")
                
                elif model_choice == "gemini":
                    # Uses Gemini 1.5 Pro via Airforce
                    ai_reply = await fetch_airforce([{"role": "user", "content": text}], "gemini-1.5-pro")

            except Exception as main_error:
                # GUARANTEED FALLBACK: If the chosen model goes down, it forces a web-search model
                try:
                    ai_reply = "[Network Switch]: " + await fetch_pollinations(text, "search")
                except Exception as fallback_error:
                    ai_reply = f"Error: Render IP was blocked by both APIs. ({str(main_error)})"

        # Calculate Latency
        time_taken = round(time.time() - start_time, 2)
        
        return {
            "text": ai_reply,
            "model": model_choice.upper(),
            "time": f"{time_taken}s"
        }
        
    except Exception as e:
        return {"text": f"Server Error: {str(e)}", "model": "SYS_ERROR", "time": "0s"}
