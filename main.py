from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx
import g4f
import time
import asyncio
import urllib.parse

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return FileResponse("static/index.html")

# 100% UPTIME DIRECT APIs (No g4f scraping required for these)
async def fetch_pollinations(prompt: str, model: str):
    # Models: 'openai' (GPT-4), 'llama' (Llama 3)
    encoded_prompt = urllib.parse.quote(prompt)
    url = f"https://text.pollinations.ai/prompt/{encoded_prompt}?model={model}"
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url)
        if response.status_code == 200:
            return response.text
        raise Exception("Pollinations busy")

# REAL VISION & FALLBACK PROCESSING
async def process_ai(model_choice: str, text: str, image_base64: str = None):
    # 1. IF THERE IS AN IMAGE (LIVE MODE / UPLOAD)
    if image_base64:
        try:
            # Blackbox is the most reliable free vision provider in g4f
            response = await asyncio.to_thread(
                g4f.ChatCompletion.create,
                model="gpt-4o",
                provider=g4f.Provider.Blackbox,
                messages=[{"role": "user", "content": text + "\n[Analyze this attached screen/image carefully]"}],
                image=image_base64.split(',')[1] if ',' in image_base64 else image_base64
            )
            return response
        except Exception as e:
            return "Vision System Error: The free vision processor is currently overloaded. Please try again."

    # 2. IF TEXT ONLY (GUARANTEED UPTIME CASCADE)
    try:
        if model_choice == "gpt-4":
            return await fetch_pollinations(text, "openai")
        elif model_choice == "llama":
            return await fetch_pollinations(text, "llama")
        elif model_choice == "deepseek":
            # Direct to g4f Deepseek Provider
            return await asyncio.to_thread(
                g4f.ChatCompletion.create, model="deepseek-coder", provider=g4f.Provider.DeepSeek,
                messages=[{"role": "user", "content": text}]
            )
        else: # Gemini or Fallback
            return await asyncio.to_thread(
                g4f.ChatCompletion.create, model="gemini-pro", provider=g4f.Provider.Blackbox,
                messages=[{"role": "user", "content": text}]
            )
    except Exception:
        # ULTIMATE FAILSAFE: If chosen model fails, force DuckDuckGo API via g4f
        return await asyncio.to_thread(
            g4f.ChatCompletion.create, model="gpt-4o", provider=g4f.Provider.DDG,
            messages=[{"role": "user", "content": text}]
        )

@app.post("/chat")
async def chat_endpoint(request: Request):
    try:
        data = await request.json()
        user_message = data.get("message")
        model_choice = data.get("model")
        image_data = data.get("image") 
        
        start_time = time.time()
        
        ai_reply = await process_ai(model_choice, user_message, image_data)
        
        time_taken = round(time.time() - start_time, 2)
        
        return {
            "text": ai_reply,
            "model": model_choice.upper(),
            "time": f"{time_taken}s"
        }
    except Exception as e:
        return {"text": f"Crucial Error: {str(e)}", "model": "SYS_ERROR", "time": "0s"}
