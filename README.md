# 🎵 YouTube MP3 Converter & Live Streaming API (FastAPI + yt-dlp)

Microservicio backend desarrollado con **FastAPI**, **yt-dlp** y **ffmpeg** para:
1. **Streaming en Vivo (sin descarga)** con latencia de 0.1 segundos.
2. **Búsqueda estructurada** de canciones y álbumes.
3. **Descarga de archivos MP3** a 320 kbps.

---

## 🚀 Despliegue con Docker (Recomendado)

### Iniciar con Docker Compose
```bash
cd api-audio
docker compose up -d --build
```

El servidor estará listo y corriendo en:
`http://localhost:8000`

---

## 📌 Endpoints de la API

### 1. 🎧 Escuchar Audio en Vivo (Streaming sin Descargar)
- **Endpoint**: `GET /api/stream?url={youtube_url_o_videoId}`
- **Ejemplo con URL**: `http://localhost:8000/api/stream?url=https://www.youtube.com/watch?v=QgRxK1ZnCA0`
- **Ejemplo con VideoId**: `http://localhost:8000/api/stream?url=QgRxK1ZnCA0`
- **Uso en HTML5 / React Native**:
  ```html
  <audio controls src="http://localhost:8000/api/stream?url=QgRxK1ZnCA0"></audio>
  ```

### 2. 🔍 Búsqueda de Canciones
- **Endpoint**: `GET /api/search?q={query}`
- **Ejemplo**: `http://localhost:8000/api/search?q=Bad+Bunny`

### 3. 📥 Descarga de Archivo MP3 a 320 kbps
- **Endpoint**: `GET /api/download?url={youtube_url_o_videoId}`
- **Ejemplo**: `http://localhost:8000/api/download?url=QgRxK1ZnCA0`

---

## 📖 Documentación Interactiva Swagger
- **Swagger UI**: `http://localhost:8000/docs`
