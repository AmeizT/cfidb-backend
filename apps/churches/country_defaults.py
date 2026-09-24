"""Country defaults from CLDR; shared by create validation and form options."""
from datetime import date
from babel import Locale, UnknownLocaleError # type: ignore
from babel.core import get_global # type: ignore
from babel.numbers import get_territory_currencies # type: ignore


def country_defaults(code):
    code = code.strip().upper()
    names = Locale('en').territories
    currencies = get_territory_currencies(code, start_date=date.today())
    if len(code) != 2 or code not in names or not currencies:
        raise ValueError('Select a supported country.')
    # Prefer English where it is an official language, matching the application's
    # existing formatting conventions; otherwise use CLDR's territory default.
    english = get_global('territory_languages').get(code, {}).get('en', {})
    locale_id = f'en_{code}' if english.get('official_status') in {'official', 'de_facto_official'} else f'und_{code}'
    try:
        locale = Locale.parse(locale_id)
    except UnknownLocaleError as exc:
        raise ValueError('No supported formatting locale for this country.') from exc
    return {
        'country': names[code],
        'country_code': code,
        'locale': f'{locale.language}-{code}',
        # In multi-tender countries prefer the national currency (e.g. NAD/ZWG).
        'currency': next((currency for currency in currencies if currency.startswith(code)), currencies[0]),
    }


def country_options():
    result = []
    for code in Locale('en').territories:
        try:
            result.append(country_defaults(code))
        except ValueError:
            pass
    return sorted(result, key=lambda item: item['country'])




COUNTRY_DEFAULTS = {
    # Southern / Eastern Africa
    "NA": {"currency": "NAD", "locale": "en-NA"},
    "NAM": {"currency": "NAD", "locale": "en-NA"},

    "KE": {"currency": "KES", "locale": "en-KE"},
    "KEN": {"currency": "KES", "locale": "en-KE"},

    "UG": {"currency": "UGX", "locale": "en-UG"},
    "UGA": {"currency": "UGX", "locale": "en-UG"},

    "TZ": {"currency": "TZS", "locale": "en-TZ"},
    "TZA": {"currency": "TZS", "locale": "en-TZ"},

    "RW": {"currency": "RWF", "locale": "en-RW"},
    "RWA": {"currency": "RWF", "locale": "en-RW"},

    "BI": {"currency": "BIF", "locale": "en-BI"},
    "BDI": {"currency": "BIF", "locale": "en-BI"},

    "ZM": {"currency": "ZMW", "locale": "en-ZM"},
    "ZMB": {"currency": "ZMW", "locale": "en-ZM"},

    "LS": {"currency": "LSL", "locale": "en-LS"},
    "LSO": {"currency": "LSL", "locale": "en-LS"},

    "AO": {"currency": "AOA", "locale": "pt-AO"},
    "AGO": {"currency": "AOA", "locale": "pt-AO"},

    # Horn of Africa
    "ET": {"currency": "ETB", "locale": "en-ET"},
    "ETH": {"currency": "ETB", "locale": "en-ET"},

    "SD": {"currency": "SDG", "locale": "en-SD"},
    "SDN": {"currency": "SDG", "locale": "en-SD"},

    "SS": {"currency": "SSP", "locale": "en-SS"},
    "SSD": {"currency": "SSP", "locale": "en-SS"},

    "ER": {"currency": "ERN", "locale": "en-ER"},
    "ERI": {"currency": "ERN", "locale": "en-ER"},

    "DJ": {"currency": "DJF", "locale": "en-DJ"},
    "DJI": {"currency": "DJF", "locale": "en-DJ"},

    "SO": {"currency": "SOS", "locale": "en-SO"},
    "SOM": {"currency": "SOS", "locale": "en-SO"},

    # Indian Ocean
    "MG": {"currency": "MGA", "locale": "en-MG"},
    "MDG": {"currency": "MGA", "locale": "en-MG"},

    "KM": {"currency": "KMF", "locale": "en-KM"},
    "COM": {"currency": "KMF", "locale": "en-KM"},

    # West Africa
    "NG": {"currency": "NGN", "locale": "en-NG"},
    "NGA": {"currency": "NGN", "locale": "en-NG"},

    # Zimbabwe
    "ZW": {"currency": "ZWG", "locale": "en-ZW"},
    "ZWE": {"currency": "ZWG", "locale": "en-ZW"},
}


COUNTRY_NAME_DEFAULTS = {
    "namibia": {"currency": "NAD", "locale": "en-NA"},
    "kenya": {"currency": "KES", "locale": "en-KE"},
    "uganda": {"currency": "UGX", "locale": "en-UG"},
    "tanzania": {"currency": "TZS", "locale": "en-TZ"},
    "zanzibar": {"currency": "TZS", "locale": "en-TZ"},
    "rwanda": {"currency": "RWF", "locale": "en-RW"},
    "burundi": {"currency": "BIF", "locale": "en-BI"},
    "zambia": {"currency": "ZMW", "locale": "en-ZM"},
    "lesotho": {"currency": "LSL", "locale": "en-LS"},
    "angola": {"currency": "AOA", "locale": "pt-AO"},
    "ethiopia": {"currency": "ETB", "locale": "en-ET"},
    "sudan": {"currency": "SDG", "locale": "en-SD"},
    "south sudan": {"currency": "SSP", "locale": "en-SS"},
    "eritrea": {"currency": "ERN", "locale": "en-ER"},
    "djibouti": {"currency": "DJF", "locale": "en-DJ"},
    "somalia": {"currency": "SOS", "locale": "en-SO"},
    "madagascar": {"currency": "MGA", "locale": "en-MG"},
    "comoros": {"currency": "KMF", "locale": "en-KM"},
    "nigeria": {"currency": "NGN", "locale": "en-NG"},
    "zimbabwe": {"currency": "ZWG", "locale": "en-ZW"},
}


def get_country_defaults(country_code="", country=""):
    code = (country_code or "").strip().upper()

    if code and code in COUNTRY_DEFAULTS:
        return COUNTRY_DEFAULTS[code]

    name = (country or "").strip().lower()

    if name and name in COUNTRY_NAME_DEFAULTS:
        return COUNTRY_NAME_DEFAULTS[name]

    return None
