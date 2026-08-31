Here I will Document my thoughts before I start the projecet and update this and remove this as I go along.

My initial thoughts based on looking at the menu is we first need to break it down into objects to represent what makes up the Menu.

So there are Menu Items along with their add-ons and dietary restrictions with cost as well. This can be an array that contains dictionaries that map Name: FoodItem, Price: Cost, Tags: VG, Spicy, Etc

MenuItems:
    name: str #Food item
    price: float #Cost
    tags: List[str] #Descriptors

Menu:
    items: List[MenuItems]


As I'm going through OpenAI's structured output similar to GenAI the top root object has to be an JSON Object so it needs a Menu Object to contain MenuItems


We can track everything in memory so we should have global variables for our data

Menus_db:
    list[
    id: str
    menu_items: dict
    ]

If we're tracking analytics then we need something to contain outputs from OpenAI

analytics_db:
    list[
        Each User Quer: dict
    ]

Look into FastAPI and learn about it with examples