"""Contexto climático (Change 024).

Os testes padrão usam respostas da Open-Meteo simuladas (MOCK). O teste
marcado como `live` consulta a API real e só roda com `pytest -m live`.
"""

import asyncio
from datetime import date

import httpx
import pytest

from OSDroupa.ai import weather as w

_REAL_ASYNC_CLIENT = httpx.AsyncClient

GEOCODE_RECIFE = {"results": [
    {"name": "Recife", "admin1": "Pernambuco", "country_code": "BR", "latitude": -8.05, "longitude": -34.9},
]}
GEOCODE_HOMONIMAS = {"results": [
    {"name": "Bom Jesus", "admin1": "Piauí", "country_code": "BR", "latitude": -9.07, "longitude": -44.36},
    {"name": "Bom Jesus", "admin1": "Rio Grande do Sul", "country_code": "BR", "latitude": -28.67, "longitude": -50.43},
]}
FORECAST = {
    "current": {"time": "2026-11-02T14:00", "temperature_2m": 29.9, "apparent_temperature": 33.4, "relative_humidity_2m": 59,
                "precipitation": 0.0, "weather_code": 0, "wind_speed_10m": 14.0, "is_day": 1},
    "hourly": {"time": [f"2026-11-02T{h:02d}:00" for h in range(24)], "precipitation_probability": [10] * 15 + [70] + [0] * 8},
    "daily": {"temperature_2m_max": [30.2], "temperature_2m_min": [24.8], "precipitation_sum": [1.2],
              "precipitation_probability_max": [70], "uv_index_max": [9.5]},
}


@pytest.fixture(autouse=True)
def clear_caches():
    w._cache.clear()
    w._places.clear()


def mock_open_meteo(monkeypatch, geocode=GEOCODE_RECIFE, forecast=FORECAST, fail=False):
    """MOCK: substitui a rede da Open-Meteo por respostas fixas."""
    calls = []

    def handler(request):
        calls.append(request.url.host)
        if fail:
            raise httpx.ConnectError("sem rede", request=request)
        return httpx.Response(200, json=geocode if "geocoding" in request.url.host else forecast)

    monkeypatch.setattr(w.httpx, "AsyncClient", lambda **kw: _REAL_ASYNC_CLIENT(transport=httpx.MockTransport(handler), **kw))
    return calls


def test_lookup_tables():
    assert len(w.UF_REGIONS) == 27 and set(w.UF_REGIONS) == set(w.UF_NAMES)
    assert w.region_for_uf("pe") == "Nordeste" and w.region_for_uf("RS") == "Sul" and w.region_for_uf("XX") == ""
    assert w.uf_from_state_name("São Paulo") == "SP" and w.uf_from_state_name("Para") == "PA"


@pytest.mark.parametrize("day,season", [
    ((1, 5), "Verão"), ((3, 19), "Verão"), ((3, 20), "Outono"), ((7, 1), "Inverno"),
    ((9, 22), "Primavera"), ((11, 2), "Primavera"), ((12, 21), "Verão"),
])
def test_southern_season(day, season):
    assert w.southern_season(date(2026, *day)) == season


@pytest.mark.parametrize("feels,rain,precip,code,expected", [
    (30, 10, 0, 1, "Quente"), (27, 0, 0, 0, "Quente"), (17, 0, 0, 0, "Frio"), (20, 59, 0, 3, "Ameno"),
    (20, 60, 0, 0, "Chuvoso"), (35, 0, 0.2, 0, "Chuvoso"), (25, 0, 0, 63, "Chuvoso"),
])
def test_classify(feels, rain, precip, code, expected):
    assert w.classify(feels, rain, precip, code) == expected


def test_context_from_mocked_api(monkeypatch):
    mock_open_meteo(monkeypatch)
    ctx = asyncio.run(w.get_weather_context("Recife", "PE"))
    assert ctx["cidade"] == "Recife" and ctx["uf"] == "PE" and ctx["regiao"] == "Nordeste"
    assert ctx["sensacao"] == 33.4 and ctx["periodo"] == "Tarde" and ctx["estacao"] == "Primavera"
    assert ctx["chuva_prob"] == 70 and ctx["categoria"] == "Chuvoso"  # 70% às 15h entra na janela de 6 h


def test_cache_avoids_second_request(monkeypatch):
    calls = mock_open_meteo(monkeypatch)
    asyncio.run(w.get_weather_context("Recife", "PE"))
    asyncio.run(w.get_weather_context("recife", "pe"))
    assert len(calls) == 2  # 1 geocoding + 1 previsão


def test_uf_disambiguates_homonyms(monkeypatch):
    mock_open_meteo(monkeypatch, geocode=GEOCODE_HOMONIMAS)
    place = asyncio.run(w.geocode("Bom Jesus", "RS"))
    assert place["uf"] == "RS" and place["latitude"] == -28.67


def test_unknown_city_and_network_failure(monkeypatch):
    mock_open_meteo(monkeypatch, geocode={"results": []})
    with pytest.raises(w.WeatherUnavailable, match="Não encontramos"):
        asyncio.run(w.get_weather_context("Xyzqwertlandia"))
    w._places.clear()
    mock_open_meteo(monkeypatch, fail=True)
    with pytest.raises(w.WeatherUnavailable, match="indisponível"):
        asyncio.run(w.get_weather_context("Curitiba", "PR"))


def test_city_name_too_short():
    with pytest.raises(w.WeatherUnavailable):
        asyncio.run(w.geocode("a"))


@pytest.mark.live
def test_live_open_meteo():
    """REAL: consulta a Open-Meteo (gratuita, sem chave)."""
    ctx = asyncio.run(w.get_weather_context("Manaus", "AM"))
    assert ctx["regiao"] == "Norte" and ctx["fonte"] == "Open-Meteo"
