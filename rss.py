import urllib.request
import xml.etree.ElementTree as ET

from bs4 import BeautifulSoup
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path
from urllib.parse import urljoin

WEB_URL = "https://www.amrest.eu/es/noticias/notas-de-prensa"
BASE_URL = "https://www.amrest.eu"
OUTPUT_FILE = Path("amrest.xml")


def descargar_pagina(numero):
    if numero == 0:
        url = WEB_URL
    else:
        url = f"{WEB_URL}?page={numero}"

    solicitud = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 Chrome/124 Safari/537.36"
            )
        },
    )

    with urllib.request.urlopen(solicitud, timeout=60) as respuesta:
        return respuesta.read()


def descargar_noticias():
    noticias = []
    enlaces_encontrados = set()

    # Lee las cinco primeras páginas del archivo de AmRest.
    for numero_pagina in range(5):
        contenido = descargar_pagina(numero_pagina)
        soup = BeautifulSoup(contenido, "html.parser")

        tarjetas = soup.select("article.news-card")

        if not tarjetas:
            break

        for tarjeta in tarjetas:
            titulo_elemento = tarjeta.select_one("h2.news--text a")
            fecha_elemento = tarjeta.select_one(".calendar")
            categoria_elemento = tarjeta.select_one(".category")
            imagen_elemento = tarjeta.select_one(".feature-image img")

            if not titulo_elemento:
                continue

            titulo = titulo_elemento.get_text(" ", strip=True)
            enlace = urljoin(BASE_URL, titulo_elemento.get("href", ""))

            if not titulo or not enlace or enlace in enlaces_encontrados:
                continue

            fecha = ""

            if fecha_elemento:
                fecha = fecha_elemento.get_text(" ", strip=True)

            categoria = ""

            if categoria_elemento:
                categoria = categoria_elemento.get_text(" ", strip=True)

            imagen = ""

            if imagen_elemento:
                imagen = urljoin(
                    BASE_URL,
                    imagen_elemento.get("src", ""),
                )

            enlaces_encontrados.add(enlace)

            noticias.append(
                {
                    "titulo": titulo,
                    "enlace": enlace,
                    "fecha": fecha,
                    "categoria": categoria,
                    "imagen": imagen,
                }
            )

    return noticias


def crear_rss(noticias):
    rss = ET.Element(
        "rss",
        {
            "version": "2.0",
            "xmlns:atom": "http://www.w3.org/2005/Atom",
            "xmlns:media": "http://search.yahoo.com/mrss/",
        },
    )

    canal = ET.SubElement(rss, "channel")

    ET.SubElement(canal, "title").text = "Notas de prensa de AmRest"
    ET.SubElement(canal, "link").text = WEB_URL
    ET.SubElement(canal, "description").text = (
        "Últimas notas de prensa y noticias para inversores de AmRest"
    )
    ET.SubElement(canal, "language").text = "es"
    ET.SubElement(canal, "lastBuildDate").text = format_datetime(
        datetime.now(timezone.utc)
    )

    enlace_atom = ET.SubElement(
        canal,
        "{http://www.w3.org/2005/Atom}link",
    )
    enlace_atom.set("href", WEB_URL)
    enlace_atom.set("rel", "self")
    enlace_atom.set("type", "application/rss+xml")

    for noticia in noticias:
        elemento = ET.SubElement(canal, "item")

        ET.SubElement(elemento, "title").text = noticia["titulo"]
        ET.SubElement(elemento, "link").text = noticia["enlace"]

        descripcion = noticia["titulo"]

        if noticia["categoria"]:
            descripcion = (
                f"Categoría: {noticia['categoria']}. "
                f"{noticia['titulo']}"
            )

        ET.SubElement(elemento, "description").text = descripcion

        identificador = ET.SubElement(elemento, "guid")
        identificador.set("isPermaLink", "true")
        identificador.text = noticia["enlace"]

        if noticia["categoria"]:
            ET.SubElement(elemento, "category").text = noticia["categoria"]

        if noticia["imagen"]:
            imagen = ET.SubElement(
                elemento,
                "{http://search.yahoo.com/mrss/}content",
            )
            imagen.set("url", noticia["imagen"])
            imagen.set("medium", "image")

        if noticia["fecha"]:
            try:
                fecha_publicacion = datetime.strptime(
                    noticia["fecha"],
                    "%d-%m-%Y",
                ).replace(tzinfo=timezone.utc)

                ET.SubElement(elemento, "pubDate").text = format_datetime(
                    fecha_publicacion
                )
            except ValueError:
                pass

    ET.indent(rss, space=" ")

    arbol = ET.ElementTree(rss)
    arbol.write(
        OUTPUT_FILE,
        encoding="utf-8",
        xml_declaration=True,
    )


def main():
    noticias = descargar_noticias()

    if not noticias:
        raise RuntimeError("No se encontraron noticias de AmRest")

    crear_rss(noticias)

    print(f"RSS creada correctamente con {len(noticias)} noticias")


if __name__ == "__main__":
    main()
