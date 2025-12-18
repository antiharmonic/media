from fastapi import FastAPI, HTTPException
from imdb import Cinemagoer

app = FastAPI()
ia = Cinemagoer()

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/search")
def search(q: str):
    try:
        movies = ia.search_movie(q)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return [{"id": m.movieID, "title": m.get("title"), "year": m.get("year"), "cover url": m.get("cover url", None)} for m in movies[:10]]

@app.get("/movie/{movie_id}")
def movie(movie_id: str):
    try:
        m = ia.get_movie(movie_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    print(m, flush=True)
    movie = {
        "id": movie_id,
        "title": m.get("title"),
        "year": m.get("year"),
        "rating": m.get("rating"),
        "genres": m.get("genres"),
        "plot": m.get("plot"),
        "cover url": m.get("cover url"),
        "full-size cover url": m.get("full-size cover url"),
    }

    if m.get("runtimes"):
       movie["runtimes"] = m.get("runtimes", [])

    return movie

