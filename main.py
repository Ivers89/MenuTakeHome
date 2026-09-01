import base64
import uuid
import time
import json
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from openai import OpenAI
from typing import Dict, List, Any

app = FastAPI()
client = OpenAI()

app.add_middleware( # Getting around Cross Origin Resource Sharing brower mechanic for local dev 
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# Models and DB
menus_db: Dict[str, dict] = {} # Stores ID and Parsed Items
analytics_db: List[dict] = [] # Holds analytics for later retrieval

# Pydantic models for chat messaging
class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]

MENU_SCHEMA = { 
    "type": "object",
    "properties": {
        "menu_items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "price": {"type": "number"},
                    "tags": {
                        "type": "array",
                        "items": {"type":"string"}
                    }
                },
                "required": ["name", "price", "tags"],
                "additionalProperties": False 
            }
        }
    },
    "required": ["menu_items"],
    "additionalProperties": False
}


# Since we'll be tracking analytics for each menu call or chat call
# Helper function for tracking analytics
def track_analytics(model: str, usage: int, latency:float, action: str):

    total_cost = usage.input_tokens * (0.15/1000000) + usage.output_tokens * (0.60/1000000)

    analytics_db.append(
        {
            "model": model,
            "input_tokens": usage.input_tokens,
            "output_tokens": usage.output_tokens,
            "cost": total_cost,
            "latency": round(latency*1000, 3),
            "action": action
        }
    )

@app.get("/")
def serve_ui():
    return FileResponse("index.html")

# Main function for uploading menus, parsing the menu using OpenAI, and saving to menus_db
@app.post("/menus")
async def upload_menu(file: UploadFile = File(...)):

    contents = await file.read()
    base64_image = base64.b64encode(contents).decode("utf-8")

    start_time = time.time()
    response = client.responses.create(
        model = "gpt-4o-mini",
        input = [
            {
                "role": "user",
                "content" : [ 
                    {"type": "input_text", "text": "Extract all menu items along with price and tags (ex: vegetarian, spicy, gf)."},
                    {"type": "input_image", "image_url": f"data:{file.content_type};base64,{base64_image}"}
                ]
            }
        ],
        text = { # structured output to ensure correct parsed responses.
            "format": {
                "type": "json_schema",
                "name": "menu_schema",
                "strict": True,
                "schema": MENU_SCHEMA
            }
        }
    )

    latency = time.time() - start_time
    track_analytics(response.model, response.usage, latency, "Upload")
    
    raw_text = response.output_text

    # Error Handling in case OpenAI responds with unexpected outputs
    # Network issues or OpenAI refusal
    if not raw_text:
        raise HTTPException(
            status_code=502,
            detail="The model returned no content. Try again or use a clearer photo."
        )

    # In case response JSON isn't valid like output being trunciated early
    try:
        parsed_menu = json.loads(raw_text) # Cast into json from output string
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=502,
            detail="Model output wasn't valid JSON. Try again or use a clearer photo."
        )

    # No menu items found on image
    if not parsed_menu.get("menu_items"):
        raise HTTPException(
            status_code=422,
            detail="No menu items were found in that image. Try a clearer or more direct photo of the menu."
        )

    menu_id = str(uuid.uuid4())
    menus_db[menu_id] = parsed_menu

    return {"id": menu_id, "menu": parsed_menu}

@app.post("/menus/{id}/chat")
async def chat_menu(id: str, chat: ChatRequest):
    if id not in menus_db: # Checks for id match in case browser still has old menu_id before restarting process
        raise HTTPException(status_code=404, detail="Menu Not Found")

    system_prompt = {
        "role": "system",
        "content": ( 
            "You are a helpful waiter. Answer questions using only the menu data. If something isn't on the menu tell the user instead of guessing. \n"
            f"Use this menu json: {json.dumps(menus_db[id])}" # Converts python objects into Json String
        )
    }    

    input_message = [system_prompt] + [m.model_dump() for m in chat.messages] # model_dumps() converts each List[ChatMessage] back into dict ["role", "content"] 

    start_time = time.time()
    response = client.responses.create(
        model = "gpt-4o-mini",
        input = input_message
    )
    latency = time.time() - start_time

    track_analytics(response.model, response.usage, latency, "Chat")

    reply = response.output_text or "Sorry, I cannot come up with a response right now. Please try again later." # If empty response then tell user error
    return {"reply": reply}

@app.get("/analytics")
def get_analytics():
    total_calls = len(analytics_db)
    if total_calls == 0:
        return {
            "totals": {
                "total_calls": 0,
                "total_tokens": 0,
                "total_cost": 0,
                "avg_latency": 0
            },
            "history": [] 
        } 

    total_tokens = sum(call["input_tokens"] + call["output_tokens"] for call in analytics_db)
    total_cost = sum(call["cost"] for call in analytics_db)
    avg_latency = sum(call["latency"] for call in analytics_db)/total_calls

    return {
            "totals": {
                "total_calls": total_calls,
                "total_tokens": total_tokens,
                "total_cost": total_cost,
                "avg_latency": avg_latency
            },
            "history": analytics_db #Return analytics_db since it logs each call. Let's us check analytics by call vs total.
        }


