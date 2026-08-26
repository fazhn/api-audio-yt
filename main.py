import os
import tempfile
import uuid
from typing import Optional
import httpx
from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
import yt_dlp

app = FastAPI(
    title="YouTube MP3 Converter & Live Streaming API",
    description="Microservicio FastAPI optimizado (0% CPU en streaming con AAC/M4A nativo y descarga de MP3 320kbps)",
    version="1.0.0"
)

# Habilitar CORS completo para peticiones desde navegadores, Swagger UI y aplicaciones móviles
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

TEMP_DIR = os.path.join(tempfile.gettempdir(), "api_audio_downloads")
os.makedirs(TEMP_DIR, exist_ok=True)


def cleanup_file(filepath: str):
    """Elimina el archivo temporal tras la descarga."""
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
    except Exception as e:
        print(f"Error eliminando archivo temporal {filepath}: {e}")


@app.get("/")
def health_check():
    return {
        "status": "ok",
        "service": "YouTube MP3 Streaming & Downloader API (FastAPI + AAC Zero-CPU Stream)",
        "version": "1.0.0"
    }


@app.get("/api/search")
def search_tracks(
    q: str = Query(..., description="Término de búsqueda o nombre de canción/artista"),
    limit: int = 15
):
    """Busca canciones en YouTube y devuelve metadatos estructurados con enlaces de streaming y descarga."""
    search_term = q.strip()
    if not search_term:
        raise HTTPException(status_code=400, detail="El parámetro de búsqueda 'q' no puede estar vacío")

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": "in_playlist",
        "default_search": f"ytsearch{limit}",
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(search_term, download=False)
            entries = info.get("entries", []) if info else []

            results = []
            for entry in entries:
                if not entry:
                    continue
                video_id = entry.get("id")
                if not video_id:
                    continue

                title = entry.get("title", "Canción de YouTube")
                uploader = entry.get("uploader") or entry.get("channel") or "Artista YouTube"
                duration = entry.get("duration") or 210

                results.append({
                    "id": f"yt-{video_id}",
                    "videoId": video_id,
                    "title": title,
                    "artist": uploader,
                    "duration": int(duration),
                    "thumbnailUrl": f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
                    "youtubeUrl": f"https://www.youtube.com/watch?v={video_id}",
                    "streamUrl": f"/api/stream?url={video_id}",
                    "downloadApiUrl": f"/api/download?url={video_id}"
                })

            return {"query": search_term, "total": len(results), "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al buscar en YouTube: {str(e)}")


@app.get("/api/stream")
async def stream_audio_by_url(
    url: str = Query(..., description="URL completa de YouTube o ID del video")
):
    """
    Escucha la canción en tiempo real (0% CPU - Native AAC/M4A Stream Proxy).
    Transmite el audio AAC nativo de YouTube sin ejecutar FFmpeg en el servidor,
    logrando 0% consumo de CPU y máxima compatibilidad con iOS, Android y Navegadores Web.
    """
    clean_url = url.strip()
    if len(clean_url) == 11 and not clean_url.startswith("http"):
        clean_url = f"https://www.youtube.com/watch?v={clean_url}"

    # Pedir formato m4a / 140 de YouTube (AAC nativo compatible con todos los dispositivos)
    ydl_opts = {
        "format": "140/m4a/bestaudio[ext=m4a]/bestaudio/best",
        "quiet": True,
        "no_warnings": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(clean_url, download=False)
            direct_audio_url = info.get("url") if info else None

            if not direct_audio_url:
                raise HTTPException(status_code=404, detail="No se pudo resolver el flujo de audio de YouTube")

            # Transmisión asíncrona de fragmentos sin reconversión (0% uso de CPU)
            client = httpx.AsyncClient(follow_redirects=True, timeout=30.0)
            req = client.build_request("GET", direct_audio_url)
            r = await client.send(req, stream=True)

            content_type = r.headers.get("content-type", "audio/mp4")

            async def chunk_generator():
                try:
                    async for chunk in r.aiter_bytes(chunk_size=65536):
                        yield chunk
                finally:
                    await r.aclose()
                    await client.aclose()

            return StreamingResponse(
                chunk_generator(),
                media_type=content_type,
                headers={
                    "Accept-Ranges": "bytes",
                    "Content-Type": content_type,
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "*",
                    "Access-Control-Allow-Headers": "*",
                }
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en streaming de audio: {str(e)}")


@app.get("/api/download")
def download_mp3_by_url(
    url: str = Query(..., description="URL completa de YouTube o ID del video"),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Convierte y descarga el audio de YouTube directamente a un archivo MP3 nativo 320kbps."""
    clean_url = url.strip()

    if len(clean_url) == 11 and not clean_url.startswith("http"):
        clean_url = f"https://www.youtube.com/watch?v={clean_url}"

    unique_id = str(uuid.uuid4())
    output_filename_base = os.path.join(TEMP_DIR, unique_id)
    final_mp3_path = f"{output_filename_base}.mp3"

    ydl_opts = {
        "format": "bestaudio/best",
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "320",
        }],
        "outtmpl": output_filename_base,
        "quiet": True,
        "no_warnings": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            meta = ydl.extract_info(clean_url, download=True)
            raw_title = meta.get("title", "cancion") if meta else "cancion"
            safe_title = "".join(c for c in raw_title if c.isalnum() or c in (" ", "_", "-")).strip() or "cancion"
            download_filename = f"{safe_title}.mp3"

        if not os.path.exists(final_mp3_path):
            raise HTTPException(status_code=500, detail="No se pudo generar el archivo MP3")

        background_tasks.add_task(cleanup_file, final_mp3_path)

        return FileResponse(
            path=final_mp3_path,
            media_type="audio/mpeg",
            filename=download_filename
        )
    except HTTPException:
        raise
    except Exception as e:
        cleanup_file(final_mp3_path)
        raise HTTPException(status_code=500, detail=f"Error en la conversión MP3: {str(e)}")
