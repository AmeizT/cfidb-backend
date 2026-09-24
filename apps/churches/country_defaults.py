"""Country defaults from CLDR; shared by create validation and form options."""
from datetime import date
from babel import Locale, UnknownLocaleError
from babel.core import get_global
from babel.numbers import get_territory_currencies


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
