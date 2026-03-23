from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import g4f
from g4f.client import Client
import time
import asyncio

app = FastAPI()

# This prevents Render routing errors
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Serve the UI
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return FileResponse("static/index.html")

# Initialize the lightweight client
g4f_client = Client()

def get_ai_answer(model_choice, user_message):
    # Match the UI names to specific g4f model endpoints
    model_map = {
        "gpt-4": "gpt-4",
        "gemini": "gemini-pro",
        "llama": "llama-3-70b",
        "deepseek": "deepseek-coder"
    }
    target = model_map.get(model_choice, "gpt-3.5-turbo")

    try:
        response = g4f_client.chat.completions.create(
            model=target,
            messages=[{"role": "user", "content": user_message}]
        )
        return response.choices[0].message.content
    except Exception as e:
        # If the free provider blocks us, automatically fallback to a super-reliable one (Blackbox)
        try:
            fallback = g4f_client.chat.completions.create(
                model="gpt-3.5-turbo",
                provider=g4f.Provider.Blackbox,
                messages=[{"role": "user", "content": user_message}]
            )
            return f"[Model Busy - Used Backup]: {fallback.choices[0].message.content}"
        except:
            return "Ciri Error: All free providers are currently overloaded. Please click Retry."

@app.post("/chat")
async def chat_endpoint(request: Request):
    try:
        data = await request.json()
        user_message = data.get("message")
        model_choice = data.get("model")
        
        start_time = time.time()

        # Run the AI request in the background so Render doesn't crash
        ai_reply = await asyncio.to_thread(get_ai_answer, model_choice, user_message)

        end_time = time.time()
        time_taken = round(end_time - start_time, 2)

        return {
            "text": ai_reply,
            "model": model_choice.upper(),
            "time": f"{time_taken}s"
        }
    except Exception as e:
        # Guarantee we send a JSON response back to the frontend even if it fails
        return {
            "text": f"Server Error: {str(e)}",
            "model": "ERROR",
            "time": "0s"
        }
