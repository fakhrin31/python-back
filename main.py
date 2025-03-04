from typing import Annotated

from fastapi import FastAPI, Path, Query

app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "Backend"}

@app.get("/about")
def about():
    return {"message": "About Me: This is my personal website."}

@app.get("/contact")
def contact():
    return {"message": "Contact Me: example@email.com"}

@app.get("/aritmatic")
def add_numbers(a: float, b: float):
    result = a + b
    return {"a": a, "b": b, "sum": result}


@app.get("/items/{item_id}")
async def read_items(
    item_id: Annotated[int, Path(title="The ID of the item to get")],
    q: Annotated[str | None, Query(alias="item-query")] = None,
):
    results = {"item_id": item_id}
    if q:
        results.update({"q": q})
    return results