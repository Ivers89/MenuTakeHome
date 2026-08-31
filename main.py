from pydantic import BaseModel
from openai import OpenAI
import base64
from fastapi import FastAPI, UploadFile, File, HTTPException


app = FastAPI()
client = OpenAI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# Models and DB
menus_db: Dict[str, dict] = {}
analytics_db: List[dict] = []

# Since OpenAI's response format doesn't work like GenAI, this isn't needed but can be used as reference for json schema
# class MenuItem(BaseModel):
#     name: str
#     price: float
#     tags: List[str]

# class Menu(BaseModel):
#     items: List[MenuItem]

class ChatRequest(BaseModel):
    messages: List[Dict[str, str]]

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
                    },
                    "required": ["name", "price", "tags"],
                    "additionalProperties": False
                }
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


# Main function for uploading menus, interpreting, and saving to db
@app.post("/menus")
async def upload_menu(file: UploadFile = File(...)):
    start_time = time.time()

    contents = await file.read()
    base64_image = base64.b64encode(contents).decode("utf-8")

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
        text = MENU_SCHEMA
    )

    latency = time.time()
    track_analytics(response.model, response.usage, latency, "Upload")
    
    menu_id = str(uuid.uuid4())
    parsed_menu = json.loads(response.output_text)
    menus_db[menu_id] = parsed_menu

    return {"id": menu_id, "menu": parsed_menu}


