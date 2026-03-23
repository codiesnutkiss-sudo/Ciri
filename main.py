from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx
import g4f
from g4f.client import Client
import time
import asyncio
import urllib.parse
import nest_asyncio

# Prevent async loop crashes on Render
nest_asyncio.apply()

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize the smart client (handles broken providers automatically)
g4f_client = Client()

@app.get("/")
async def root():
    return FileResponse("static/index.html")

# 100% UPTIME DIRECT API (Bypasses g4f completely)
async def process_text_pollinations(prompt: str, model: str):
    encoded_prompt = urllib.parse.quote(prompt)
    url = f"https://text.pollinations.ai/prompt/{encoded_prompt}?model={model}"
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url)
        if response.status_code == 200:
            return response.text
        raise Exception("Direct API busy")

async def process_ai(model_choice: str, text: str, image_base64: str = None):
    # 1. VISION MODE (If image is sent via Live Mode or Upload)
    if image_base64:
        try:
            # We use the standard OpenAI payload format. 
            # The g4f client will automatically route this to Bing/Gemini Vision.
            response = await asyncio.to_thread(
                g4f_client.chat.completions.create,
                model="gpt-4o",
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": text + "\n[System: Analyze this attached image/screen carefully.]"},
                        {"type": "image_url", "image_url": {"url": image_base64}}
                    ]
                }]
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Vision System Error: Ensure your screen isn't completely black. Details: {str(e)}"

    # 2. TEXT MODE (Guaranteed cascade)
    try:
        if model_choice == "gpt-4":
            return await process_text_pollinations(text, "openai")
        elif model_choice == "llama":
            return await process_text_pollinations(text, "llama")
        elif model_choice == "deepseek":
            # Let the smart client find a working Deepseek provider
            res = await asyncio.to_thread(
                g4f_client.chat.completions.create,
                model="deepseek-coder",
                messages=[{"role": "user", "content": text}]
            )
            return res.choices[0].message.content
        elif model_choice == "gemini":
            # Let the smart client find a working Gemini provider
            res = await asyncio.to_thread(
                g4f_client.chat.completions.create,
                model="gemini-pro",
                messages=[{"role": "user", "content": text}]
            )
            return res.choices[0].message.content
    except Exception as e:
        # ULTIMATE FALLBACK: If g4f models fail, fallback to a guaranteed search model
        try:
            return f"[Used Backup Model]: " + await process_text_pollinations(text, "search")
        except:
            return "Crucial Error: All systems currently overloaded. Please retry in 10 seconds."

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
