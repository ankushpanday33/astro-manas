"""Low-precision ephemeris for the demo (Meeus, "Astronomical Algorithms", ch. 25 and 47, main terms only).

Accuracy is roughly 0.01 deg for the Sun and 0.1 deg for the Moon, enough to show the pipeline, NOT enough for
production: a Nakshatra or Tithi can flip near a boundary. Production must swap this module for a validated
sidereal ephemeris (Drik, Lahiri) behind the same three functions: sun_moon_sidereal, ayanamsha_lahiri, sunrise_utc.
"""
from __future__ import annotations

import math
from datetime import date, datetime, timedelta, timezone

D2R = math.pi / 180


def _jd(dt_utc: datetime) -> float:
    return dt_utc.timestamp() / 86400.0 + 2440587.5


def _norm(x: float) -> float:
    return x % 360.0


def _sun_tropical(T: float) -> float:
    L0 = 280.46646 + 36000.76983 * T + 0.0003032 * T * T
    M = 357.52911 + 35999.05029 * T - 0.0001537 * T * T
    C = ((1.914602 - 0.004817 * T - 0.000014 * T * T) * math.sin(M * D2R)
         + (0.019993 - 0.000101 * T) * math.sin(2 * M * D2R) + 0.000289 * math.sin(3 * M * D2R))
    omega = 125.04 - 1934.136 * T
    return _norm(L0 + C - 0.00569 - 0.00478 * math.sin(omega * D2R))


# (D, M, M', F, coefficient) for the Moon's longitude, largest terms of Meeus table 47.A
_MOON_TERMS = [
    (0, 0, 1, 0, 6.288774), (2, 0, -1, 0, 1.274027), (2, 0, 0, 0, 0.658314), (0, 0, 2, 0, 0.213618),
    (0, 1, 0, 0, -0.185116), (0, 0, 0, 2, -0.114332), (2, 0, -2, 0, 0.058793), (2, -1, -1, 0, 0.057066),
    (2, 0, 1, 0, 0.053322), (2, -1, 0, 0, 0.045758), (0, 1, -1, 0, -0.040923), (1, 0, 0, 0, -0.034720),
    (0, 1, 1, 0, -0.030383), (2, 0, 0, -2, 0.015327), (0, 0, 1, 2, -0.012528), (0, 0, 1, -2, 0.010980),
    (4, 0, -1, 0, 0.010675), (0, 0, 3, 0, 0.010034), (4, 0, -2, 0, 0.008548), (2, 1, -1, 0, -0.007888),
    (2, 1, 0, 0, -0.006766), (1, 0, -1, 0, -0.005163), (1, 1, 0, 0, 0.004987), (2, -1, 1, 0, 0.004036),
    (2, 0, 2, 0, 0.003994), (4, 0, 0, 0, 0.003861), (2, 0, -3, 0, 0.003665), (0, 1, -2, 0, -0.002689),
    (2, 0, -1, 2, -0.002602), (2, -1, -2, 0, 0.002390), (1, 0, 1, 0, -0.002348), (2, -2, 0, 0, 0.002236),
]


def _moon_tropical(T: float) -> float:
    Lp = 218.3164477 + 481267.88123421 * T
    D = 297.8501921 + 445267.1114034 * T
    M = 357.5291092 + 35999.0502909 * T
    Mp = 134.9633964 + 477198.8675055 * T
    F = 93.2720950 + 483202.0175233 * T
    E = 1 - 0.002516 * T
    lon = Lp
    for d, m, mp, f, coef in _MOON_TERMS:
        arg = (d * D + m * M + mp * Mp + f * F) * D2R
        lon += coef * (E ** abs(m)) * math.sin(arg)
    omega = 125.04452 - 1934.136261 * T
    return _norm(lon - 0.00478 * math.sin(omega * D2R))


def ayanamsha_lahiri(dt_utc: datetime) -> float:
    """Lahiri ayanamsha, linear approximation: 23.853 deg at J2000, precessing 50.2788 arcsec per year."""
    years = (_jd(dt_utc) - 2451545.0) / 365.25
    return 23.853 + years * 50.2788 / 3600.0


def sun_moon_sidereal(dt_utc: datetime) -> tuple[float, float]:
    T = (_jd(dt_utc) - 2451545.0) / 36525.0
    ay = ayanamsha_lahiri(dt_utc)
    return _norm(_sun_tropical(T) - ay), _norm(_moon_tropical(T) - ay)


def sunrise_utc(day: date, lat: float, lon: float) -> datetime | None:
    """NOAA sunrise for the local civil date `day` at (lat, lon). None in polar day or night."""
    n = (datetime(day.year, day.month, day.day, 12, tzinfo=timezone.utc) - datetime(2000, 1, 1, 12, tzinfo=timezone.utc)).days
    j_star = n - lon / 360.0
    M = _norm(357.5291 + 0.98560028 * j_star)
    Cc = 1.9148 * math.sin(M * D2R) + 0.02 * math.sin(2 * M * D2R) + 0.0003 * math.sin(3 * M * D2R)
    lam = _norm(M + Cc + 180 + 102.9372)
    j_transit = 2451545.0 + j_star + 0.0053 * math.sin(M * D2R) - 0.0069 * math.sin(2 * lam * D2R)
    dec = math.asin(math.sin(lam * D2R) * math.sin(23.44 * D2R))
    cos_w = (math.sin(-0.833 * D2R) - math.sin(lat * D2R) * math.sin(dec)) / (math.cos(lat * D2R) * math.cos(dec))
    if not -1 <= cos_w <= 1:
        return None
    w = math.degrees(math.acos(cos_w))
    j_rise = j_transit - w / 360.0
    return datetime.fromtimestamp((j_rise - 2440587.5) * 86400.0, tz=timezone.utc)
