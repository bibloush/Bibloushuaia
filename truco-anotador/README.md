# Anotador de Truco - Heber Frau

App para Android inspirada en un anotador clasico argentino. Dos equipos (Nos / Ellos), tantos dibujados con fosforos, partidos de 15 o 30, sumar y restar, deshacer, nuevo partido y guardado automatico.

**Autor visible:** Hecha por Heber Frau.

## Descargar la APK
Una vez finalizada la compilacion: https://github.com/bibloush/Bibloushuaia/releases/tag/truco-v1.0

Archivo de instalacion: **Truco-Heber-Frau.apk**. Tambien se descarga desde Actions > Compilar APK Truco Heber Frau > Artifacts.

## Instalacion en Android
Descargar el archivo APK desde Releases; abrirlo en el telefono y autorizar la instalacion de apps de esta fuente si Android lo solicita.

## Musica
La marcha suena suavemente mientras la app esta abierta. Se puede silenciar desde el menu. Cuando la app se minimiza la musica se pausa.

Interpretacion: **United States Marine Band**, "San Lorenzo" (Cayetano Alberto Silva), grabacion de 1992 publicada en dominio publico. Fuente: https://commons.wikimedia.org/wiki/File:San_Lorenzo_-_U.S._Marine_Band.ogg

La compilacion de GitHub Actions descarga esta fuente de Wikimedia Commons y la convierte a MP3 para incorporarla **sin necesidad de Internet al utilizar la app**.

## Compilar
Se usa GitHub Actions con JDK 17 y Gradle 8.10.2. El workflow es .github/workflows/truco-apk.yml en la rama truco-anotador. El proyecto Android esta dentro de la carpeta truco-anotador.

El APK se firma con clave de depuracion para pruebas y uso personal. Para publicacion en Google Play, generar una compilacion release firmada de forma segura.
