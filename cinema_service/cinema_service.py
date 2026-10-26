from fastapi import FastAPI, HTTPException
import imdbinfo

app = FastAPI()

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/search")
def search(q: str):
    try:
        results = imdbinfo.search_title(q)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    out = []
    for t in results.titles[:10]:
        out.append({
            "id": t.imdbId,
            "title": t.title,
            "year": t.year,
            "cover url": t.cover_url,
        })
    return out

@app.get("/movie/{movie_id}")
def movie(movie_id: str):
    if not movie_id.startswith("tt"):
        movie_id = "tt" + movie_id
    try:
        m = imdbinfo.get_movie(movie_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {
        "id": movie_id,
        "title": m.title,
        "year": m.year,
        "rating": m.rating,
        "cover url": m.cover_url,
        "full-size cover url": m.cover_url,
        "plot": [m.plot] if m.plot else [],
        "runtimes": [str(m.duration)] if m.duration else [],
    }
