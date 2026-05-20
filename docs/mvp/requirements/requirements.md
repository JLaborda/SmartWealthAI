# REQUISITOS DEL SPRINT 0: MVP Screener Magic Formula
Objetivo Principal: Crear un pipeline básico en Python que descargue datos financieros de un grupo muy reducido de acciones, calcule un ranking simple y lo muestre por consola.

1. Requisitos Funcionales:

Input: El sistema partirá de una lista estática (hardcodeada) de solo 5 a 10 tickers conocidos (ej. ["AAPL", "MSFT", "GOOGL", "JNJ", "KO"]). Nota: No vamos a descargar todo el S&P 500 hoy para evitar bloqueos de la API y tiempos de espera.

Procesamiento: El sistema se conectará a una API gratuita (recomiendo yfinance para empezar rápido) y descargará las dos métricas proxy para la Fórmula Mágica:

* Return on Capital (ROC) o en su defecto Return on Equity (ROE) / Return on Assets (ROA).

* Earnings Yield o en su defecto su inverso, el P/E Ratio (Price-to-Earnings).

* Lógica de Negocio: El sistema ordenará las acciones dándole una puntuación del 1 al N en cada métrica, y sumará ambas puntuaciones para obtener el "Magic Rank" final.

Output: El sistema imprimirá por consola (con un simple print o usando Pandas) el ranking final ordenado de la mejor opción a la peor.

2. Requisitos Técnicos:

Lenguaje: Python 3.x

Librerías externas: yfinance (para datos) y pandas (para manejar el ranking fácilmente).

Control de versiones: Git en local (un par de commits).

Prohibiciones absolutas para hoy: Nada de bases de datos, nada de interfaces gráficas (GUI), nada de Docker, nada de Machine Learning, nada de descargar miles de tickers. Todo eso es Versión 2.0.