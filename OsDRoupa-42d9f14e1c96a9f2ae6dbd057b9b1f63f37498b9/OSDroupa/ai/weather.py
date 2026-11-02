"""Contexto climático real via Open-Meteo (Change 024).

Executado somente no servidor Reflex. A Open-Meteo não exige chave; apenas a
cidade/UF sai do servidor.
"""

import time
import unicodedata
from datetime import date, datetime, timezone

import httpx

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
WEATHER_TIMEOUT = 8.0  # segundos
CACHE_TTL_SECONDS = 30 * 60

HOT_FEELS_LIKE = 27.0
COLD_FEELS_LIKE = 17.0
RAIN_PROBABILITY = 60
RAIN_WINDOW_HOURS = 6

UF_NAMES = {
    "AC": "Acre", "AL": "Alagoas", "AP": "Amapá", "AM": "Amazonas", "BA": "Bahia",
    "CE": "Ceará", "DF": "Distrito Federal", "ES": "Espírito Santo", "GO": "Goiás",
    "MA": "Maranhão", "MT": "Mato Grosso", "MS": "Mato Grosso do Sul", "MG": "Minas Gerais",
    "PA": "Pará", "PB": "Paraíba", "PR": "Paraná", "PE": "Pernambuco", "PI": "Piauí",
    "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte", "RS": "Rio Grande do Sul",
    "RO": "Rondônia", "RR": "Roraima", "SC": "Santa Catarina", "SP": "São Paulo",
    "SE": "Sergipe", "TO": "Tocantins",
}

UF_REGIONS = {
    **dict.fromkeys(["AC", "AP", "AM", "PA", "RO", "RR", "TO"], "Norte"),
    **dict.fromkeys(["AL", "BA", "CE", "MA", "PB", "PE", "PI", "RN", "SE"], "Nordeste"),
    **dict.fromkeys(["DF", "GO", "MT", "MS"], "Centro-Oeste"),
    **dict.fromkeys(["ES", "MG", "RJ", "SP"], "Sudeste"),
    **dict.fromkeys(["PR", "RS", "SC"], "Sul"),
}

WMO_CONDITIONS = {
    0: "Céu limpo", 1: "Predominantemente limpo", 2: "Parcialmente nublado", 3: "Nublado",
    45: "Neblina", 48: "Neblina com geada",
    51: "Garoa fraca", 53: "Garoa", 55: "Garoa forte", 56: "Garoa congelante", 57: "Garoa congelante",
    61: "Chuva fraca", 63: "Chuva", 65: "Chuva forte", 66: "Chuva congelante", 67: "Chuva congelante",
    71: "Neve fraca", 73: "Neve", 75: "Neve forte", 77: "Grãos de neve",
    80: "Pancadas de chuva fracas", 81: "Pancadas de chuva", 82: "Pancadas de chuva fortes",
    85: "Pancadas de neve", 86: "Pancadas de neve fortes",
    95: "Trovoadas", 96: "Trovoadas com granizo", 99: "Trovoadas com granizo",
}
RAINY_CODES = {51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82, 95, 96, 99}

_cache: dict[str, tuple[float, dict]] = {}
_places: dict[str, dict] = {}  # cidades não mudam de coordenada; sem expiração


class WeatherUnavailable(Exception):
    """Previsão indisponível; a mensagem é segura para exibir ao usuário."""


def _fold(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text or "")
    return "".join(ch for ch in normalized if not unicodedata.combining(ch)).casefold().strip()


def region_for_uf(uf: str) -> str:
    return UF_REGIONS.get((uf or "").strip().upper(), "")


def uf_from_state_name(name: str) -> str:
    folded = _fold(name)
    return next((uf for uf, full in UF_NAMES.items() if _fold(full) == folded), "")


def southern_season(day: date) -> str:
    """Estação astronômica aproximada no hemisfério sul."""
    md = (day.month, day.day)
    if md >= (12, 21) or md < (3, 20):
        return "Verão"
    if md < (6, 21):
        return "Outono"
    if md < (9, 22):
        return "Inverno"
    return "Primavera"


def day_period(hour: int) -> str:
    if 5 <= hour < 12:
        return "Manhã"
    if 12 <= hour < 18:
        return "Tarde"
    if 18 <= hour < 24:
        return "Noite"
    return "Madrugada"


def classify(feels_like: float, rain_probability: int, precipitation: float, weather_code: int) -> str:
    """Converte a previsão nas categorias usadas por `lookDoDia` (RF-CLIMA-03)."""
    if rain_probability >= RAIN_PROBABILITY or precipitation > 0 or weather_code in RAINY_CODES:
        return "Chuvoso"
    if feels_like >= HOT_FEELS_LIKE:
        return "Quente"
    if feels_like <= COLD_FEELS_LIKE:
        return "Frio"
    return "Ameno"


async def geocode(city: str, uf: str = "") -> dict:
    """Localiza uma cidade brasileira; usa a UF para desempatar homônimas."""
    city = (city or "").strip()[:80]
    if len(city) < 2:
        raise WeatherUnavailable("Informe o nome de uma cidade.")
    params = {"name": city, "countryCode": "BR", "language": "pt", "count": 10, "format": "json"}
    try:
        async with httpx.AsyncClient(timeout=WEATHER_TIMEOUT) as client:
            response = await client.get(GEOCODING_URL, params=params)
        response.raise_for_status()
        results = response.json().get("results") or []
    except (httpx.HTTPError, ValueError, AttributeError) as exc:
        raise WeatherUnavailable("A previsão do tempo está indisponível no momento.") from exc
    results = [r for r in results if isinstance(r, dict) and r.get("country_code") == "BR"]
    if uf:
        same_state = [r for r in results if uf_from_state_name(str(r.get("admin1") or "")) == uf.strip().upper()]
        results = same_state or results
    if not results:
        raise WeatherUnavailable("Não encontramos essa cidade no Brasil.")
    best = results[0]
    return {
        "cidade": str(best.get("name") or city),
        "uf": uf_from_state_name(str(best.get("admin1") or "")) or uf.strip().upper(),
        "latitude": float(best["latitude"]),
        "longitude": float(best["longitude"]),
    }


async def forecast(latitude: float, longitude: float) -> dict:
    params = {
        "latitude": round(latitude, 4),
        "longitude": round(longitude, 4),
        "timezone": "auto",
        "forecast_days": 1,
        "current": "temperature_2m,apparent_temperature,relative_humidity_2m,precipitation,weather_code,wind_speed_10m,is_day",
        "hourly": "precipitation_probability",
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,uv_index_max",
    }
    try:
        async with httpx.AsyncClient(timeout=WEATHER_TIMEOUT) as client:
            response = await client.get(FORECAST_URL, params=params)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data.get("current"), dict):
            raise ValueError("Resposta sem dados atuais.")
        return data
    except (httpx.HTTPError, ValueError, AttributeError) as exc:
        raise WeatherUnavailable("A previsão do tempo está indisponível no momento.") from exc


def _first(values, default=0.0):
    return values[0] if isinstance(values, list) and values and values[0] is not None else default


def build_context(place: dict, data: dict) -> dict:
    """Normaliza a resposta da Open-Meteo no contrato `WeatherContext`."""
    current = data.get("current") or {}
    daily = data.get("daily") or {}
    hourly = data.get("hourly") or {}
    local_now = str(current.get("time") or "")
    try:
        local_dt = datetime.fromisoformat(local_now)
    except ValueError:
        local_dt = datetime.now()

    # Probabilidade máxima de chuva nas próximas horas a partir da hora local atual.
    times = hourly.get("time") or []
    probs = hourly.get("precipitation_probability") or []
    current_hour = local_dt.strftime("%Y-%m-%dT%H:00")
    start = next((i for i, t in enumerate(times) if t >= current_hour), 0)
    window = [p for p in probs[start:start + RAIN_WINDOW_HOURS] if p is not None]
    rain_probability = int(max(window) if window else _first(daily.get("precipitation_probability_max"), 0))

    code = int(current.get("weather_code") or 0)
    feels_like = float(current.get("apparent_temperature") or current.get("temperature_2m") or 0.0)
    precipitation = float(current.get("precipitation") or 0.0)
    uf = str(place.get("uf") or "")
    return {
        "cidade": str(place.get("cidade") or ""),
        "uf": uf,
        "regiao": region_for_uf(uf),
        "temperatura": round(float(current.get("temperature_2m") or 0.0), 1),
        "sensacao": round(feels_like, 1),
        "minima": round(float(_first(daily.get("temperature_2m_min"))), 1),
        "maxima": round(float(_first(daily.get("temperature_2m_max"))), 1),
        "umidade": int(current.get("relative_humidity_2m") or 0),
        "chuva_prob": rain_probability,
        "chuva_mm": round(float(_first(daily.get("precipitation_sum"))), 1),
        "vento_kmh": round(float(current.get("wind_speed_10m") or 0.0), 1),
        "uv_max": round(float(_first(daily.get("uv_index_max"))), 1),
        "condicao": WMO_CONDITIONS.get(code, "Condição não informada"),
        "weather_code": code,
        "data_local": local_dt.date().isoformat(),
        "hora_local": local_dt.strftime("%H:%M"),
        "periodo": day_period(local_dt.hour),
        "estacao": southern_season(local_dt.date()),
        "categoria": classify(feels_like, rain_probability, precipitation, code),
        "fonte": "Open-Meteo",
        "consultado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "manual": False,
    }


async def get_weather_context(city: str, uf: str = "") -> dict:
    """Geocodifica a cidade, consulta a previsão e devolve o contexto (com cache de 30 min)."""
    place_key = f"{_fold(city)}|{(uf or '').strip().upper()}"
    place = _places.get(place_key)
    if place is None:
        place = await geocode(city, uf)
        _places[place_key] = place
    key = f"{place['latitude']:.2f},{place['longitude']:.2f}"
    cached = _cache.get(key)
    if cached and time.monotonic() - cached[0] < CACHE_TTL_SECONDS:
        return cached[1]
    context = build_context(place, await forecast(place["latitude"], place["longitude"]))
    _cache[key] = (time.monotonic(), context)
    return context
