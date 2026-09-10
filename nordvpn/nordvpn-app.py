#!/usr/bin/env python3
import os
# The Shield Pi CRT launcher is designed in physical 720x576 pixels.
# Force GTK to one logical pixel per CRT pixel so desktop DPI settings
# cannot magnify this TV interface.
os.environ['GDK_SCALE'] = '1'
os.environ['GDK_DPI_SCALE'] = '1.0'

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib, GdkPixbuf

import json
import re
import time
import ipaddress
import subprocess
import threading
import urllib.parse
import urllib.request

APP_TITLE = 'Shield NordVPN Android CRT v10.19 COMBAT PACK'
CFG_DIR = os.path.expanduser('~/.config/shield-nordvpn')
FAV_FILE = os.path.join(CFG_DIR, 'favorites.json')
RECENT_FILE = os.path.join(CFG_DIR, 'recent.json')
ASSET_DIR = os.path.expanduser('~/.local/share/shield-nordvpn')
HERO_MAP = os.path.join(ASSET_DIR, 'hero-world.png')
SYSTEM_SHIELD = os.path.join(ASSET_DIR, 'system-shield.png')
BAND_ART = os.path.join(ASSET_DIR, 'shield-band.png')
SYSTEM_PAGE_BG = os.path.join(ASSET_DIR, 'system-page-bg.png')
VPN_PAGE_BG = os.path.join(ASSET_DIR, 'vpn-page-bg.png')
DNS_PAGE_BG = os.path.join(ASSET_DIR, 'dns-page-bg.png')
STATUS_PAGE_BG = os.path.join(ASSET_DIR, 'status-page-bg.png')
COUNTRY_GRID_BG = os.path.join(ASSET_DIR, 'country-grid-bg.png')
COUNTRY_PREVIEW_BG = os.path.join(ASSET_DIR, 'country-preview-bg.png')
FLAG_CACHE_DIR = os.path.expanduser('~/.cache/shield-nordvpn/flags')
CITY_FLAG_CACHE_DIR = os.path.expanduser('~/.cache/shield-nordvpn/cityflags')
CITY_FLAG_ASSET_DIR = os.path.join(ASSET_DIR, 'cityflags')
FOOTER_ART = os.path.join(ASSET_DIR, 'footer-shield.png')
FLAG_CDN = 'https://flagcdn.com/160x120/{code}.png'
WIKIDATA_API = 'https://www.wikidata.org/w/api.php'
COMMONS_API = 'https://commons.wikimedia.org/w/api.php'

NORD_DNS = ('103.86.96.100', '103.86.99.100')
API_COUNTRIES = 'https://api.nordvpn.com/v1/servers/countries'
API_RECOMMEND = 'https://api.nordvpn.com/v1/servers/recommendations'
ANSI_RE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

GERMAN_COUNTRY_NAMES = {'AD': 'Andorra', 'AE': 'Vereinigte Arabische Emirate', 'AF': 'Afghanistan', 'AG': 'Antigua und Barbuda', 'AI': 'Anguilla', 'AL': 'Albanien', 'AM': 'Armenien', 'AO': 'Angola', 'AQ': 'Antarktis', 'AR': 'Argentinien', 'AS': 'Amerikanisch-Samoa', 'AT': 'Österreich', 'AU': 'Australien', 'AW': 'Aruba', 'AX': 'Ålandinseln', 'AZ': 'Aserbaidschan', 'BA': 'Bosnien und Herzegowina', 'BB': 'Barbados', 'BD': 'Bangladesch', 'BE': 'Belgien', 'BF': 'Burkina Faso', 'BG': 'Bulgarien', 'BH': 'Bahrain', 'BI': 'Burundi', 'BJ': 'Benin', 'BL': 'St. Barthélemy', 'BM': 'Bermuda', 'BN': 'Brunei Darussalam', 'BO': 'Bolivien', 'BQ': 'Karibische Niederlande', 'BR': 'Brasilien', 'BS': 'Bahamas', 'BT': 'Bhutan', 'BV': 'Bouvetinsel', 'BW': 'Botsuana', 'BY': 'Belarus', 'BZ': 'Belize', 'CA': 'Kanada', 'CC': 'Kokosinseln', 'CD': 'Kongo-Kinshasa', 'CF': 'Zentralafrikanische Republik', 'CG': 'Kongo-Brazzaville', 'CH': 'Schweiz', 'CI': 'Côte d’Ivoire', 'CK': 'Cookinseln', 'CL': 'Chile', 'CM': 'Kamerun', 'CN': 'China', 'CO': 'Kolumbien', 'CR': 'Costa Rica', 'CU': 'Kuba', 'CV': 'Cabo Verde', 'CW': 'Curaçao', 'CX': 'Weihnachtsinsel', 'CY': 'Zypern', 'CZ': 'Tschechien', 'DE': 'Deutschland', 'DJ': 'Dschibuti', 'DK': 'Dänemark', 'DM': 'Dominica', 'DO': 'Dominikanische Republik', 'DZ': 'Algerien', 'EC': 'Ecuador', 'EE': 'Estland', 'EG': 'Ägypten', 'EH': 'Westsahara', 'ER': 'Eritrea', 'ES': 'Spanien', 'ET': 'Äthiopien', 'FI': 'Finnland', 'FJ': 'Fidschi', 'FK': 'Falklandinseln', 'FM': 'Mikronesien', 'FO': 'Färöer', 'FR': 'Frankreich', 'GA': 'Gabun', 'GB': 'Vereinigtes Königreich', 'GD': 'Grenada', 'GE': 'Georgien', 'GF': 'Französisch-Guayana', 'GG': 'Guernsey', 'GH': 'Ghana', 'GI': 'Gibraltar', 'GL': 'Grönland', 'GM': 'Gambia', 'GN': 'Guinea', 'GP': 'Guadeloupe', 'GQ': 'Äquatorialguinea', 'GR': 'Griechenland', 'GS': 'Südgeorgien und die Südlichen Sandwichinseln', 'GT': 'Guatemala', 'GU': 'Guam', 'GW': 'Guinea-Bissau', 'GY': 'Guyana', 'HK': 'Sonderverwaltungsregion Hongkong', 'HM': 'Heard und McDonaldinseln', 'HN': 'Honduras', 'HR': 'Kroatien', 'HT': 'Haiti', 'HU': 'Ungarn', 'ID': 'Indonesien', 'IE': 'Irland', 'IL': 'Israel', 'IM': 'Isle of Man', 'IN': 'Indien', 'IO': 'Britisches Territorium im Indischen Ozean', 'IQ': 'Irak', 'IR': 'Iran', 'IS': 'Island', 'IT': 'Italien', 'JE': 'Jersey', 'JM': 'Jamaika', 'JO': 'Jordanien', 'JP': 'Japan', 'KE': 'Kenia', 'KG': 'Kirgisistan', 'KH': 'Kambodscha', 'KI': 'Kiribati', 'KM': 'Komoren', 'KN': 'St. Kitts und Nevis', 'KP': 'Nordkorea', 'KR': 'Südkorea', 'KW': 'Kuwait', 'KY': 'Kaimaninseln', 'KZ': 'Kasachstan', 'LA': 'Laos', 'LB': 'Libanon', 'LC': 'St. Lucia', 'LI': 'Liechtenstein', 'LK': 'Sri Lanka', 'LR': 'Liberia', 'LS': 'Lesotho', 'LT': 'Litauen', 'LU': 'Luxemburg', 'LV': 'Lettland', 'LY': 'Libyen', 'MA': 'Marokko', 'MC': 'Monaco', 'MD': 'Republik Moldau', 'ME': 'Montenegro', 'MF': 'St. Martin', 'MG': 'Madagaskar', 'MH': 'Marshallinseln', 'MK': 'Nordmazedonien', 'ML': 'Mali', 'MM': 'Myanmar', 'MN': 'Mongolei', 'MO': 'Sonderverwaltungsregion Macau', 'MP': 'Nördliche Marianen', 'MQ': 'Martinique', 'MR': 'Mauretanien', 'MS': 'Montserrat', 'MT': 'Malta', 'MU': 'Mauritius', 'MV': 'Malediven', 'MW': 'Malawi', 'MX': 'Mexiko', 'MY': 'Malaysia', 'MZ': 'Mosambik', 'NA': 'Namibia', 'NC': 'Neukaledonien', 'NE': 'Niger', 'NF': 'Norfolkinsel', 'NG': 'Nigeria', 'NI': 'Nicaragua', 'NL': 'Niederlande', 'NO': 'Norwegen', 'NP': 'Nepal', 'NR': 'Nauru', 'NU': 'Niue', 'NZ': 'Neuseeland', 'OM': 'Oman', 'PA': 'Panama', 'PE': 'Peru', 'PF': 'Französisch-Polynesien', 'PG': 'Papua-Neuguinea', 'PH': 'Philippinen', 'PK': 'Pakistan', 'PL': 'Polen', 'PM': 'St. Pierre und Miquelon', 'PN': 'Pitcairninseln', 'PR': 'Puerto Rico', 'PS': 'Palästinensische Autonomiegebiete', 'PT': 'Portugal', 'PW': 'Palau', 'PY': 'Paraguay', 'QA': 'Katar', 'RE': 'Réunion', 'RO': 'Rumänien', 'RS': 'Serbien', 'RU': 'Russland', 'RW': 'Ruanda', 'SA': 'Saudi-Arabien', 'SB': 'Salomonen', 'SC': 'Seychellen', 'SD': 'Sudan', 'SE': 'Schweden', 'SG': 'Singapur', 'SH': 'St. Helena', 'SI': 'Slowenien', 'SJ': 'Spitzbergen und Jan Mayen', 'SK': 'Slowakei', 'SL': 'Sierra Leone', 'SM': 'San Marino', 'SN': 'Senegal', 'SO': 'Somalia', 'SR': 'Suriname', 'SS': 'Südsudan', 'ST': 'São Tomé und Príncipe', 'SV': 'El Salvador', 'SX': 'Sint Maarten', 'SY': 'Syrien', 'SZ': 'Eswatini', 'TC': 'Turks- und Caicosinseln', 'TD': 'Tschad', 'TF': 'Französische Süd- und Antarktisgebiete', 'TG': 'Togo', 'TH': 'Thailand', 'TJ': 'Tadschikistan', 'TK': 'Tokelau', 'TL': 'Timor-Leste', 'TM': 'Turkmenistan', 'TN': 'Tunesien', 'TO': 'Tonga', 'TR': 'Türkei', 'TT': 'Trinidad und Tobago', 'TV': 'Tuvalu', 'TW': 'Taiwan', 'TZ': 'Tansania', 'UA': 'Ukraine', 'UG': 'Uganda', 'UM': 'Amerikanische Überseeinseln', 'US': 'Vereinigte Staaten', 'UY': 'Uruguay', 'UZ': 'Usbekistan', 'VA': 'Vatikanstadt', 'VC': 'St. Vincent und die Grenadinen', 'VE': 'Venezuela', 'VG': 'Britische Jungferninseln', 'VI': 'Amerikanische Jungferninseln', 'VN': 'Vietnam', 'VU': 'Vanuatu', 'WF': 'Wallis und Futuna', 'WS': 'Samoa', 'YE': 'Jemen', 'YT': 'Mayotte', 'ZA': 'Südafrika', 'ZM': 'Sambia', 'ZW': 'Simbabwe'}
ENGLISH_COUNTRY_CODES = {'afghanistan': 'AF', 'albania': 'AL', 'algeria': 'DZ', 'american samoa': 'AS', 'andorra': 'AD', 'angola': 'AO', 'anguilla': 'AI', 'antarctica': 'AQ', 'antigua and barbuda': 'AG', 'arab republic of egypt': 'EG', 'argentina': 'AR', 'argentine republic': 'AR', 'armenia': 'AM', 'aruba': 'AW', 'australia': 'AU', 'austria': 'AT', 'azerbaijan': 'AZ', 'bahamas': 'BS', 'bahrain': 'BH', 'bangladesh': 'BD', 'barbados': 'BB', 'belarus': 'BY', 'belgium': 'BE', 'belize': 'BZ', 'benin': 'BJ', 'bermuda': 'BM', 'bhutan': 'BT', 'bolivarian republic of venezuela': 'VE', 'bolivia': 'BO', 'bolivia plurinational state of': 'BO', 'bolivia, plurinational state of': 'BO', 'bonaire sint eustatius and saba': 'BQ', 'bonaire, sint eustatius and saba': 'BQ', 'bosnia and herzegovina': 'BA', 'botswana': 'BW', 'bouvet island': 'BV', 'brazil': 'BR', 'british indian ocean territory': 'IO', 'british virgin islands': 'VG', 'brunei': 'BN', 'brunei darussalam': 'BN', 'bulgaria': 'BG', 'burkina faso': 'BF', 'burundi': 'BI', 'cabo verde': 'CV', 'cambodia': 'KH', 'cameroon': 'CM', 'canada': 'CA', 'cape verde': 'CV', 'cayman islands': 'KY', 'central african republic': 'CF', 'chad': 'TD', 'chile': 'CL', 'china': 'CN', 'christmas island': 'CX', 'cocos (keeling) islands': 'CC', 'colombia': 'CO', 'commonwealth of dominica': 'DM', 'commonwealth of the bahamas': 'BS', 'commonwealth of the northern mariana islands': 'MP', 'comoros': 'KM', 'congo': 'CG', 'congo the democratic republic of the': 'CD', 'congo, the democratic republic of the': 'CD', 'cook islands': 'CK', 'costa rica': 'CR', 'cote d ivoire': 'CI', 'croatia': 'HR', 'cuba': 'CU', 'curaçao': 'CW', 'cyprus': 'CY', 'czech republic': 'CZ', 'czechia': 'CZ', "côte d'ivoire": 'CI', "democratic people's republic of korea": 'KP', 'democratic republic of sao tome and principe': 'ST', 'democratic republic of timor-leste': 'TL', 'democratic socialist republic of sri lanka': 'LK', 'denmark': 'DK', 'djibouti': 'DJ', 'dominica': 'DM', 'dominican republic': 'DO', 'eastern republic of uruguay': 'UY', 'ecuador': 'EC', 'egypt': 'EG', 'el salvador': 'SV', 'equatorial guinea': 'GQ', 'eritrea': 'ER', 'estonia': 'EE', 'eswatini': 'SZ', 'ethiopia': 'ET', 'falkland islands (malvinas)': 'FK', 'faroe islands': 'FO', 'federal democratic republic of ethiopia': 'ET', 'federal democratic republic of nepal': 'NP', 'federal republic of germany': 'DE', 'federal republic of nigeria': 'NG', 'federal republic of somalia': 'SO', 'federated states of micronesia': 'FM', 'federative republic of brazil': 'BR', 'fiji': 'FJ', 'finland': 'FI', 'france': 'FR', 'french guiana': 'GF', 'french polynesia': 'PF', 'french republic': 'FR', 'french southern territories': 'TF', 'gabon': 'GA', 'gabonese republic': 'GA', 'gambia': 'GM', 'georgia': 'GE', 'germany': 'DE', 'ghana': 'GH', 'gibraltar': 'GI', 'grand duchy of luxembourg': 'LU', 'great britain': 'GB', 'greece': 'GR', 'greenland': 'GL', 'grenada': 'GD', 'guadeloupe': 'GP', 'guam': 'GU', 'guatemala': 'GT', 'guernsey': 'GG', 'guinea': 'GN', 'guinea-bissau': 'GW', 'guyana': 'GY', 'haiti': 'HT', 'hashemite kingdom of jordan': 'JO', 'heard island and mcdonald islands': 'HM', 'hellenic republic': 'GR', 'holy see (vatican city state)': 'VA', 'honduras': 'HN', 'hong kong': 'HK', 'hong kong special administrative region of china': 'HK', 'hungary': 'HU', 'iceland': 'IS', 'independent state of papua new guinea': 'PG', 'independent state of samoa': 'WS', 'india': 'IN', 'indonesia': 'ID', 'iran': 'IR', 'iran islamic republic of': 'IR', 'iran, islamic republic of': 'IR', 'iraq': 'IQ', 'ireland': 'IE', 'islamic republic of afghanistan': 'AF', 'islamic republic of iran': 'IR', 'islamic republic of mauritania': 'MR', 'islamic republic of pakistan': 'PK', 'isle of man': 'IM', 'israel': 'IL', 'italian republic': 'IT', 'italy': 'IT', 'ivory coast': 'CI', 'jamaica': 'JM', 'japan': 'JP', 'jersey': 'JE', 'jordan': 'JO', 'kazakhstan': 'KZ', 'kenya': 'KE', 'kingdom of bahrain': 'BH', 'kingdom of belgium': 'BE', 'kingdom of bhutan': 'BT', 'kingdom of cambodia': 'KH', 'kingdom of denmark': 'DK', 'kingdom of eswatini': 'SZ', 'kingdom of lesotho': 'LS', 'kingdom of morocco': 'MA', 'kingdom of norway': 'NO', 'kingdom of saudi arabia': 'SA', 'kingdom of spain': 'ES', 'kingdom of sweden': 'SE', 'kingdom of thailand': 'TH', 'kingdom of the netherlands': 'NL', 'kingdom of tonga': 'TO', 'kiribati': 'KI', "korea democratic people's republic of": 'KP', 'korea republic of': 'KR', 'korea south': 'KR', "korea, democratic people's republic of": 'KP', 'korea, republic of': 'KR', 'kosovo': 'XK', 'kuwait': 'KW', 'kyrgyz republic': 'KG', 'kyrgyzstan': 'KG', "lao people's democratic republic": 'LA', 'laos': 'LA', 'latvia': 'LV', 'lebanese republic': 'LB', 'lebanon': 'LB', 'lesotho': 'LS', 'liberia': 'LR', 'libya': 'LY', 'liechtenstein': 'LI', 'lithuania': 'LT', 'luxembourg': 'LU', 'macao': 'MO', 'macao special administrative region of china': 'MO', 'macedonia': 'MK', 'madagascar': 'MG', 'malawi': 'MW', 'malaysia': 'MY', 'maldives': 'MV', 'mali': 'ML', 'malta': 'MT', 'marshall islands': 'MH', 'martinique': 'MQ', 'mauritania': 'MR', 'mauritius': 'MU', 'mayotte': 'YT', 'mexico': 'MX', 'micronesia federated states of': 'FM', 'micronesia, federated states of': 'FM', 'moldova': 'MD', 'moldova republic of': 'MD', 'moldova, republic of': 'MD', 'monaco': 'MC', 'mongolia': 'MN', 'montenegro': 'ME', 'montserrat': 'MS', 'morocco': 'MA', 'mozambique': 'MZ', 'myanmar': 'MM', 'namibia': 'NA', 'nauru': 'NR', 'nepal': 'NP', 'netherlands': 'NL', 'new caledonia': 'NC', 'new zealand': 'NZ', 'nicaragua': 'NI', 'niger': 'NE', 'nigeria': 'NG', 'niue': 'NU', 'norfolk island': 'NF', 'north korea': 'KP', 'north macedonia': 'MK', 'northern mariana islands': 'MP', 'norway': 'NO', 'oman': 'OM', 'pakistan': 'PK', 'palau': 'PW', 'palestine': 'PS', 'palestine state of': 'PS', 'palestine, state of': 'PS', 'panama': 'PA', 'papua new guinea': 'PG', 'paraguay': 'PY', "people's democratic republic of algeria": 'DZ', "people's republic of bangladesh": 'BD', "people's republic of china": 'CN', 'peru': 'PE', 'philippines': 'PH', 'pitcairn': 'PN', 'plurinational state of bolivia': 'BO', 'poland': 'PL', 'portugal': 'PT', 'portuguese republic': 'PT', 'principality of andorra': 'AD', 'principality of liechtenstein': 'LI', 'principality of monaco': 'MC', 'puerto rico': 'PR', 'qatar': 'QA', 'republic of albania': 'AL', 'republic of angola': 'AO', 'republic of armenia': 'AM', 'republic of austria': 'AT', 'republic of azerbaijan': 'AZ', 'republic of belarus': 'BY', 'republic of benin': 'BJ', 'republic of bosnia and herzegovina': 'BA', 'republic of botswana': 'BW', 'republic of bulgaria': 'BG', 'republic of burundi': 'BI', 'republic of cabo verde': 'CV', 'republic of cameroon': 'CM', 'republic of chad': 'TD', 'republic of chile': 'CL', 'republic of colombia': 'CO', 'republic of costa rica': 'CR', 'republic of croatia': 'HR', 'republic of cuba': 'CU', 'republic of cyprus': 'CY', "republic of côte d'ivoire": 'CI', 'republic of djibouti': 'DJ', 'republic of ecuador': 'EC', 'republic of el salvador': 'SV', 'republic of equatorial guinea': 'GQ', 'republic of estonia': 'EE', 'republic of fiji': 'FJ', 'republic of finland': 'FI', 'republic of ghana': 'GH', 'republic of guatemala': 'GT', 'republic of guinea': 'GN', 'republic of guinea-bissau': 'GW', 'republic of guyana': 'GY', 'republic of haiti': 'HT', 'republic of honduras': 'HN', 'republic of iceland': 'IS', 'republic of india': 'IN', 'republic of indonesia': 'ID', 'republic of iraq': 'IQ', 'republic of kazakhstan': 'KZ', 'republic of kenya': 'KE', 'republic of kiribati': 'KI', 'republic of latvia': 'LV', 'republic of liberia': 'LR', 'republic of lithuania': 'LT', 'republic of madagascar': 'MG', 'republic of malawi': 'MW', 'republic of maldives': 'MV', 'republic of mali': 'ML', 'republic of malta': 'MT', 'republic of mauritius': 'MU', 'republic of moldova': 'MD', 'republic of mozambique': 'MZ', 'republic of myanmar': 'MM', 'republic of namibia': 'NA', 'republic of nauru': 'NR', 'republic of nicaragua': 'NI', 'republic of north macedonia': 'MK', 'republic of palau': 'PW', 'republic of panama': 'PA', 'republic of paraguay': 'PY', 'republic of peru': 'PE', 'republic of poland': 'PL', 'republic of san marino': 'SM', 'republic of senegal': 'SN', 'republic of serbia': 'RS', 'republic of seychelles': 'SC', 'republic of sierra leone': 'SL', 'republic of singapore': 'SG', 'republic of slovenia': 'SI', 'republic of south africa': 'ZA', 'republic of south sudan': 'SS', 'republic of suriname': 'SR', 'republic of tajikistan': 'TJ', 'republic of the congo': 'CG', 'republic of the gambia': 'GM', 'republic of the marshall islands': 'MH', 'republic of the niger': 'NE', 'republic of the philippines': 'PH', 'republic of the sudan': 'SD', 'republic of trinidad and tobago': 'TT', 'republic of tunisia': 'TN', 'republic of türkiye': 'TR', 'republic of uganda': 'UG', 'republic of uzbekistan': 'UZ', 'republic of vanuatu': 'VU', 'republic of yemen': 'YE', 'republic of zambia': 'ZM', 'republic of zimbabwe': 'ZW', 'romania': 'RO', 'russia': 'RU', 'russian federation': 'RU', 'rwanda': 'RW', 'rwandese republic': 'RW', 'réunion': 'RE', 'saint barthélemy': 'BL', 'saint helena ascension and tristan da cunha': 'SH', 'saint helena, ascension and tristan da cunha': 'SH', 'saint kitts and nevis': 'KN', 'saint lucia': 'LC', 'saint martin (french part)': 'MF', 'saint pierre and miquelon': 'PM', 'saint vincent and the grenadines': 'VC', 'samoa': 'WS', 'san marino': 'SM', 'sao tome and principe': 'ST', 'saudi arabia': 'SA', 'senegal': 'SN', 'serbia': 'RS', 'seychelles': 'SC', 'sierra leone': 'SL', 'singapore': 'SG', 'sint maarten (dutch part)': 'SX', 'slovak republic': 'SK', 'slovakia': 'SK', 'slovenia': 'SI', 'socialist republic of viet nam': 'VN', 'solomon islands': 'SB', 'somalia': 'SO', 'south africa': 'ZA', 'south georgia and the south sandwich islands': 'GS', 'south korea': 'KR', 'south sudan': 'SS', 'spain': 'ES', 'sri lanka': 'LK', 'state of israel': 'IL', 'state of kuwait': 'KW', 'state of qatar': 'QA', 'sudan': 'SD', 'sultanate of oman': 'OM', 'suriname': 'SR', 'svalbard and jan mayen': 'SJ', 'sweden': 'SE', 'swiss confederation': 'CH', 'switzerland': 'CH', 'syria': 'SY', 'syrian arab republic': 'SY', 'taiwan': 'TW', 'taiwan province of china': 'TW', 'taiwan, province of china': 'TW', 'tajikistan': 'TJ', 'tanzania': 'TZ', 'tanzania united republic of': 'TZ', 'tanzania, united republic of': 'TZ', 'thailand': 'TH', 'the state of eritrea': 'ER', 'the state of palestine': 'PS', 'timor-leste': 'TL', 'togo': 'TG', 'togolese republic': 'TG', 'tokelau': 'TK', 'tonga': 'TO', 'trinidad and tobago': 'TT', 'tunisia': 'TN', 'turkey': 'TR', 'turkmenistan': 'TM', 'turks and caicos islands': 'TC', 'tuvalu': 'TV', 'türkiye': 'TR', 'uganda': 'UG', 'ukraine': 'UA', 'union of the comoros': 'KM', 'united arab emirates': 'AE', 'united kingdom': 'GB', 'united kingdom of great britain and northern ireland': 'GB', 'united mexican states': 'MX', 'united republic of tanzania': 'TZ', 'united states': 'US', 'united states minor outlying islands': 'UM', 'united states of america': 'US', 'uruguay': 'UY', 'uzbekistan': 'UZ', 'vanuatu': 'VU', 'venezuela': 'VE', 'venezuela bolivarian republic of': 'VE', 'venezuela, bolivarian republic of': 'VE', 'viet nam': 'VN', 'vietnam': 'VN', 'virgin islands british': 'VG', 'virgin islands of the united states': 'VI', 'virgin islands u.s.': 'VI', 'virgin islands, british': 'VG', 'virgin islands, u.s.': 'VI', 'wallis and futuna': 'WF', 'western sahara': 'EH', 'yemen': 'YE', 'zambia': 'ZM', 'zimbabwe': 'ZW', 'åland islands': 'AX'}

CATEGORY_GROUPS = [
    ('LETZTE', 'recent'),
    ('FAVORITEN', 'favorites'),
    ('A-D', ('A', 'D')),
    ('E-G', ('E', 'G')),
    ('H-K', ('H', 'K')),
    ('L-O', ('L', 'O')),
    ('P-S', ('P', 'S')),
    ('T-Z', ('T', 'Z')),
]


def clean(text):
    return ANSI_RE.sub('', text or '').strip()


def run_cmd(args, timeout=50):
    env = os.environ.copy()
    env['LC_ALL'] = 'C'
    env['LANG'] = 'C'
    try:
        p = subprocess.run(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout,
            env=env,
        )
        return p.returncode, clean(p.stdout)
    except Exception as e:
        return 1, str(e)


def kv(text):
    out = {}
    for line in (text or '').splitlines():
        if ':' not in line:
            continue
        k, v = line.split(':', 1)
        out[k.strip().lower()] = v.strip()
    return out


def is_on(value):
    return str(value).strip().lower() in ('on', 'enabled', 'yes', 'true')


def pretty(token):
    return str(token or '').replace('_', ' ').strip()


def tokenise(name):
    return re.sub(r'\s+', '_', str(name or '').strip())


def alpha_initial(name):
    text = str(name or '').strip().upper()
    if not text:
        return ''
    first = text[0]
    return {'Ä':'A', 'Ö':'O', 'Ü':'U', 'É':'E', 'È':'E', 'Ç':'C'}.get(first, first)


def parse_tokens(text):
    result = []
    for raw_line in (text or '').replace('\r', '\n').splitlines():
        line = raw_line.strip()
        if not line:
            continue
        low = line.lower()
        if low.startswith(('a new version', 'tip:', 'usage:', 'commands:')):
            continue
        if ':' in line and low.startswith(
            ('countries', 'available countries', 'cities', 'available cities', 'groups', 'available groups')
        ):
            line = line.split(':', 1)[1].strip()
        for item in re.split(r'\s{2,}|,', line):
            item = item.strip(' \t,;-')
            if not item:
                continue
            # CLI normally uses underscore for multi-word locations.
            if ' ' in item and '_' not in item:
                for sub in item.split():
                    if sub and sub not in result:
                        result.append(sub)
            elif item not in result:
                result.append(item)
    return result


def read_json_file(path, default):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            value = json.load(f)
        return value
    except Exception:
        return default


def write_json_file(path, value):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def api_json(url, timeout=12):
    req = urllib.request.Request(
        url,
        headers={
            'User-Agent': 'ShieldNordVPN/10.18-SecondLevelPreview',
            'Accept': 'application/json',
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode('utf-8', errors='replace'))


class ShieldNordVPN(Gtk.Window):
    def __init__(self):
        GLib.set_prgname('shield-nordvpn')
        super().__init__(title=APP_TITLE)
        try:
            self.set_wmclass('shield-nordvpn', 'ShieldNordVPN')
        except Exception:
            pass

        # Match the exact CRT geometry used by shield-launcher-test.py.
        self.set_size_request(720, 576)
        self.set_default_size(720, 576)
        self.set_resizable(False)
        self.set_decorated(False)
        self.fullscreen()
        self.connect('destroy', Gtk.main_quit)
        self.connect('key-press-event', self.on_key)
        self.connect('key-release-event', self.on_key_release)

        self.busy = False
        self.refresh_running = False
        self.status_data = {}
        self.settings_data = {}
        self.countries = []
        self.country_ids = {}
        self.country_codes = {}
        self.favorites = read_json_file(FAV_FILE, [])
        self.recent = read_json_file(RECENT_FILE, [])

        self.mode = 'home'               # home/settings/status/country/server/dns
        self.home_category = 2           # A-D by default
        # Home carousel mirrors the original Shield launcher app row: four 164x102 tiles are
        # visible, LEFT/RIGHT moves the global selection and the row slides.
        self.home_items = []
        self.home_item_index = 0
        self.home_view_start = 0
        self.home_visible_count = 4
        self.selected_country = None
        self.selected_server = None
        self.country_tab = 'cities'
        # Country detail carousel mirrors HOME: four 164x102 cards, horizontal only.
        self.country_visible_count = 4
        self.country_city_index = 0
        self.country_city_view_start = 0
        self.country_server_index = 0
        self.country_server_view_start = 0
        self.country_detail_return_tab = 'cities'
        # TV/D-pad focus model: rows of controls plus a separately focusable left rail.
        self.nav_rows = []
        self.nav_row = 0
        self.nav_col = 0
        self.in_rail = False
        self.last_content_focus = None
        self.return_mode = 'home'
        self.widget_targets = {}
        self.ok_down = False
        self.ok_long_fired = False
        self.ok_timer = 0
        self.dns_buffers = ['', '', '']
        self.dns_index = 0
        self.flag_pending = set()
        self.city_flag_pending = set()
        self.city_flag_failed = set()
        self.wikidata_country_qids = {}
        self._armor_pending = False
        os.makedirs(FLAG_CACHE_DIR, exist_ok=True)
        os.makedirs(CITY_FLAG_CACHE_DIR, exist_ok=True)

        self.install_css()
        self.build_ui()
        self.show_all()

        GLib.idle_add(self.load_countries)
        GLib.idle_add(self.refresh_all)
        GLib.timeout_add_seconds(5, self.refresh_all)

    # ---------------- visual ----------------
    def install_css(self):
        css = b'''
        window { background:#020806; color:#fff; }
        .topbar { background:#06140e; border:2px solid #19e978; border-radius:10px; padding:6px 12px; }
        .brand { font-size:22px; font-weight:900; color:#ffffff; }
        .statusline { font-size:13px; font-weight:800; color:#e9f5ed; }
        .hero { background:#07150d; border:2px solid #42f58b; border-radius:10px; }
        .hero-connected { border:3px solid #45e37a; }
        .hero-title { font-size:23px; font-weight:900; color:#fff; }
        .armor-title { font-size:23px; font-weight:900; letter-spacing:1px; }
        .armor-offline { color:#f2f4f3; }
        .armor-arming { color:#ffb000; }
        .armor-active { color:#ff3a2f; }
        .hero-sub { font-size:12px; color:#d3dfd7; }
        .section { font-size:18px; font-weight:900; color:#fff; }
        .muted { font-size:12px; color:#aab8af; }
        .tabs { background:transparent; padding:0; }
        .tab { min-height:30px; font-size:11px; font-weight:900; padding:1px 5px; border:2px solid #238452; border-radius:7px; }
        .tabactive { background:#123a23; border:3px solid #45e37a; }
        .countrycard { font-weight:900; padding:0; border:2px solid #2f6e4a; border-radius:7px; }
        .countryflagbox { background:#0a100d; }
        .countrynamebar { background:rgba(3,8,5,0.90); border-top:1px solid #3c7857; padding:3px 5px 2px 5px; }
        .countryname { font-size:14px; font-weight:900; color:#fff; padding:0; }
        .countrymeta { font-size:10px; color:#95a49a; }
        .citycard { min-width:164px; min-height:102px; font-size:12px; font-weight:900; padding:0; border:2px solid #2f6e4a; border-radius:7px; }
        .cityflagbox { background:#08110c; }
        .citynamebar { background:rgba(3,8,5,0.92); border-top:1px solid #3c7857; padding:2px 5px; }
        .cityname { font-size:14px; font-weight:900; color:#fff; }
        .serverbadge { background:rgba(2,10,6,0.88); border:1px solid #3c7857; border-radius:4px; padding:2px 4px; }
        .serverbadge-text { font-size:9px; font-weight:900; color:#9dffc4; }
        .countrypage { background:#020806; }
        .countryhead { background:#06140e; border:2px solid #19e978; border-radius:9px; padding:6px 10px; }
        .countryhead-title { font-size:22px; font-weight:900; color:#ffffff; letter-spacing:1px; }
        .countryhead-sub { font-size:10px; font-weight:800; color:#65d995; letter-spacing:1px; }
        .countrybadge { font-size:10px; font-weight:900; color:#74ffa8; border:1px solid #2c8d57; border-radius:5px; padding:4px 7px; }
        .countryquick { min-height:44px; font-size:15px; font-weight:900; background:#0a8d46; border:3px solid #6affad; }
        .countrycarousel { background:#03100a; border:1px solid #1f6c46; border-radius:8px; padding:4px; }
        .countrynote { font-size:10px; font-weight:800; color:#8fe0ab; }
        .servergrid-title { font-size:27px; font-weight:900; color:#f4fff8; letter-spacing:1px; }
        .servergrid-sub { font-size:12px; font-weight:800; color:#67e29d; letter-spacing:1px; }
        .servergrid-summary { font-size:12px; font-weight:900; color:#72f6a7; }
        .servergrid-control { min-height:36px; font-size:11px; font-weight:900; padding:1px 6px; border:2px solid #2e8e57; border-radius:6px; background:#06150d; }
        .servergrid-control:focus { border:3px solid #6affad; background:#123a23; }
        .servergrid-note { font-size:10px; font-weight:800; color:#9cf0bb; }
        .card { min-height:48px; font-size:14px; font-weight:900; padding:4px 6px; }
        .countrycard:focus, .citycard:focus, .card:focus, button:focus { border:4px solid #45e37a; background:#153a22; }
        button { color:#f7faf8; background:#0b1710; border:2px solid #2d6d48; border-radius:7px; }
        .primary { min-height:52px; font-size:17px; font-weight:900; background:#0a8d46; border:3px solid #6affad; }
        .danger { border:2px solid #8a5252; }
        .activechoice { background:#17301f; border:3px solid #45e37a; }
        .detail { font-family:monospace; font-size:14px; color:#e5ece7; }
        .dnsdisplay { font-family:monospace; font-size:17px; font-weight:900; color:#fff; background:#101713; border:2px solid #314239; padding:7px; }
        .keypad { min-width:82px; min-height:42px; font-size:18px; font-weight:900; }
        .bandframe { background:transparent; border:0; padding:0; }
        .securetitle { color:#ffffff; font-size:15px; font-weight:900; letter-spacing:1px; }
        .securetitle-active { color:#ff3030; }
        .securesub { color:#6fe89f; font-size:9px; font-weight:700; letter-spacing:1px; }
        .midpanel { background:#03110a; border:1px solid #1f6c46; border-radius:8px; padding:2px 10px; }
        .midline { color:#2db36b; font-size:13px; font-weight:900; }
        .midlabel { color:#f5fff9; font-size:12px; font-weight:900; letter-spacing:1px; }
        .midsub { color:#91d7ae; font-size:9px; font-weight:700; letter-spacing:1px; }
        .footerbox { background:transparent; padding:2px 8px; }
        .footer { font-size:10px; font-weight:800; color:#d4e0d8; }
        .systembtn { min-width:92px; min-height:28px; font-size:11px; font-weight:900; letter-spacing:1px; padding:0 8px; border:2px solid #45e37a; border-radius:5px; background:#07150d; color:#ffffff; }
        .systembtn:focus { border:3px solid #8bffb7; background:#123a23; }
        .systempage { background:#020806; }
        .systemhead { background:#06140e; border:2px solid #19e978; border-radius:9px; padding:8px 12px; }
        .systembrand { font-size:24px; font-weight:900; color:#ffffff; letter-spacing:1px; }
        .systemtag { font-size:10px; font-weight:800; color:#79dca2; letter-spacing:1px; }
        .systemstate { font-size:12px; font-weight:900; color:#ffffff; }
        .systemstate-active { color:#ff3030; }
        .systemtile { min-width:316px; min-height:132px; padding:0; border:2px solid #2e7a4e; border-radius:7px; background:#07150d; }
        .systemtile:focus { border:4px solid #45e37a; background:#0b2214; }
        .systemtile-mark { font-size:28px; font-weight:900; color:#45e37a; }
        .systemtile-title { font-size:20px; font-weight:900; color:#ffffff; letter-spacing:1px; }
        .systemtile-sub { font-size:11px; font-weight:700; color:#98bca6; }
        .systemstrip { background:#03110a; border:1px solid #2c8d57; border-radius:6px; padding:5px 9px; }
        .systemstrip-title { font-size:12px; font-weight:900; color:#eafff0; letter-spacing:1px; }
        .systemstrip-sub { font-size:9px; font-weight:700; color:#5edb8e; letter-spacing:1px; }
        .systemtitle { font-size:23px; font-weight:900; color:#fff; padding:6px 0; }
        .previewpanel { background:#06120d; border:2px solid #2b8453; border-radius:7px; padding:7px; }
        .previewpanel-title { font-size:13px; font-weight:900; color:#eafff0; letter-spacing:1px; }
        .previewinfo { font-size:12px; color:#b7d3c0; }
        .previewlist { min-height:41px; font-size:13px; font-weight:900; padding:3px 8px; }
        .previewlist:focus { border:3px solid #45e37a; background:#123a23; }
        .systemtile-vertical { min-width:157px; min-height:206px; padding:3px; border:2px solid #2e7a4e; border-radius:7px; background:#06120d; }
        .systemtile-vertical:focus { border:4px solid #45e37a; background:#0b2214; }
        .systemtile-vmark { font-size:42px; font-weight:900; color:#45e37a; }
        .systemtile-vtitle { font-size:22px; font-weight:900; color:#ffffff; letter-spacing:1px; }
        .systemtile-vsub { font-size:11px; font-weight:800; color:#72d99b; }
        .statusbig { font-size:18px; font-weight:900; color:#ffffff; }
        .statusgood { font-size:13px; font-weight:900; color:#45e37a; }
        .statusbad { font-size:13px; font-weight:900; color:#ff3030; }
        .statusmeta { font-family:monospace; font-size:13px; color:#e7f1ea; }
        .exactsys-head { background:#04140c; border:2px solid #2ce979; border-radius:8px; padding:6px 10px; }
        .exactsys-title { font-size:23px; font-weight:900; color:#ffffff; letter-spacing:1px; }
        .exactsys-sub { font-size:12px; font-weight:800; color:#40d9a0; }
        .exactsys-motto { font-size:9px; font-weight:800; color:#50dca0; letter-spacing:1px; }
        .exactsys-tile { min-width:159px; min-height:268px; padding:4px; border:2px solid #2e9a5c; border-radius:7px; background:#04120b; }
        .exactsys-tile:focus { border:4px solid #51ff9a; background:#071b10; }
        .exactsys-headrow { background:#061a10; border:1px solid #1e8650; border-radius:5px; padding:3px 4px; }
        .exactsys-headtext { font-size:10px; font-weight:900; color:#f3fff7; letter-spacing:1px; }
        .exactsys-row { font-size:9px; color:#d3e8d9; }
        .exactsys-value { font-size:9px; font-weight:900; color:#ffffff; }
        .exactsys-good { color:#3cff88; font-weight:900; }
        .exactsys-bad { color:#ff3030; font-weight:900; }
        .exactsys-line { background:#0a2a19; min-height:1px; }
        .exactsys-strip { background:#071a10; border:1px solid #2ca663; border-radius:5px; padding:3px 5px; }
        .exactsys-striptext { font-size:9px; font-weight:900; color:#d8ffea; }
        .exactsys-icon { font-size:28px; font-weight:900; color:#4eff91; }
        .exactsys-bigname { font-size:20px; font-weight:900; color:#ffffff; letter-spacing:1px; }
        .exactsys-bigsub { font-size:10px; font-weight:800; color:#59dba0; }
        .exactsys-mapframe { background:#03130b; border:1px solid #2a9459; border-radius:5px; padding:2px; }
        .exactsys-country { font-size:8px; font-weight:800; color:#ffffff; border:1px solid #28764b; border-radius:3px; padding:2px; }
        .exactsys-bars { font-size:25px; font-weight:900; color:#3cff88; }
        .exactsys-chart { font-size:9px; color:#56d99b; }
        .exactsys-secureband { background:#031109; border:1px solid #2d995c; border-radius:5px; padding:4px 8px; }
        .exactsys-securetitle { font-size:13px; font-weight:900; color:#f5fff9; letter-spacing:1px; }
        .system-overlay-hit { background: rgba(0,0,0,0.01); border:2px solid transparent; border-radius:8px; }
        .system-overlay-hit:focus { background: rgba(0,0,0,0.08); border:3px solid #7dffb0; border-radius:10px; }
        .second-hotspot { background: rgba(0,0,0,0.01); border:2px solid transparent; border-radius:8px; }
        .second-hotspot:focus { background: rgba(0,25,12,0.15); border:3px solid #7dffb0; border-radius:8px; }
        .second-live { background: rgba(2,14,8,0.94); color:#f4fff7; font-size:12px; font-weight:900; padding:2px 6px; }
        .second-value { background: rgba(2,15,8,0.92); color:#f4fff7; font-size:12px; font-weight:900; padding:1px 4px; }
        .second-value-good { color:#39ff83; }
        .second-value-bad { color:#ff4040; }
        .serverpreview-live { background:#03160c; color:#d9ffe8; font-size:11px; font-weight:900; padding:2px 6px; }
        .serverpreview-title { background:#03160c; color:#f4fff7; font-size:25px; font-weight:900; padding:1px 5px; }
        .serverpreview-sub { background:#03160c; color:#48e58d; font-size:12px; font-weight:800; padding:1px 5px; }
        .serverpreview-info { background:#041b10; color:#5df0a0; font-size:11px; font-weight:800; padding:1px 5px; }
        .serverpreview-tab { min-width:74px; min-height:27px; font-size:10px; font-weight:900; color:#eafff0; background:#061b10; border:1px solid #30bf72; border-radius:4px; padding:0; }
        .serverpreview-tab:focus, .serverpreview-tab.tabactive { border:3px solid #71ffad; background:#0b3520; }
        .serverpreview-card { min-width:164px; min-height:102px; padding:0; border:2px solid #28bd6b; border-radius:4px; background:#06140d; }
        .serverpreview-card:focus { border:4px solid #86ffb7; background:#0c2718; }
        .serverpreview-namebar { background:rgba(2,12,7,0.94); border-top:1px solid #29a862; padding:3px; }
        .serverpreview-name { font-size:14px; font-weight:900; color:#effff5; }
        .serverpreview-badge { background:rgba(1,10,5,0.90); color:#82ffb6; font-size:9px; font-weight:900; padding:2px 4px; }
        .serverpreview-footerbtn { min-width:76px; min-height:29px; font-size:10px; font-weight:900; color:#eafff0; background:#06180e; border:2px solid #42df84; border-radius:5px; padding:0; }
        .serverpreview-footerbtn:focus { border:3px solid #8affba; background:#0b3420; }
        .quitbtn { min-width:74px; min-height:28px; font-size:10px; font-weight:900; color:#fff; background:#20100d; border:2px solid #ff6b4a; border-radius:5px; padding:0; }
        .quitbtn:focus { border:3px solid #ff9b75; background:#401711; }
        scrollbar slider { min-width:10px; min-height:22px; }
        '''
        p = Gtk.CssProvider()
        p.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), p, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def build_ui(self):
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        content.set_size_request(720, 576)
        content.set_border_width(8)
        self.add(content)

        top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=7)
        top.set_size_request(-1, 52)
        top.get_style_context().add_class('topbar')
        icon_path = '/usr/share/icons/hicolor/scalable/apps/nordvpn.svg'
        if os.path.exists(icon_path):
            try:
                logo_pix = GdkPixbuf.Pixbuf.new_from_file_at_scale(icon_path, 30, 30, True)
                logo = Gtk.Image.new_from_pixbuf(logo_pix)
                logo.set_size_request(30, 30)
                top.pack_start(logo, False, False, 0)
            except Exception:
                pass
        brand = Gtk.Label(label='NordVPN')
        brand.set_xalign(0)
        brand.get_style_context().add_class('brand')
        top.pack_start(brand, False, False, 0)
        self.top_status = Gtk.Label(label='Protokoll: -    |    Neue IP: -    |    Verbindungszeit: -')
        self.top_status.set_xalign(1)
        self.top_status.get_style_context().add_class('statusline')
        top.pack_end(self.top_status, True, True, 0)
        self.top_bar = top
        content.pack_start(top, False, False, 0)

        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.NONE)
        # Important for the 720x576 CRT: the large System/Settings pages must
        # not force the HOME page to adopt their height, otherwise the bottom
        # control row with the round SY button gets pushed off screen.
        self.stack.set_hhomogeneous(False)
        self.stack.set_vhomogeneous(False)
        self.stack.set_size_request(696, 454)
        self.stack.set_hexpand(True)
        self.stack.set_vexpand(True)
        content.pack_start(self.stack, True, True, 0)

        self.build_home()
        self.build_settings()
        self.build_status()
        self.build_country_detail()
        self.build_server_detail()
        self.build_dns()
        self.build_dns_keypad()
        self.build_system_menu()

        footer_overlay = Gtk.Overlay()
        footer_overlay.set_size_request(-1, 38)
        footer_overlay.set_vexpand(False)
        footer_overlay.set_hexpand(True)
        if os.path.exists(FOOTER_ART):
            try:
                fpix = GdkPixbuf.Pixbuf.new_from_file_at_scale(FOOTER_ART, 696, 38, False)
                footer_bg = Gtk.Image.new_from_pixbuf(fpix)
            except Exception:
                footer_bg = Gtk.Box()
        else:
            footer_bg = Gtk.Box()
        footer_overlay.add(footer_bg)

        footer_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        footer_box.set_size_request(-1, 38)
        footer_box.get_style_context().add_class('footerbox')
        self.footer = Gtk.Label(label='← → Länder    OK verbinden    OK halten Details')
        self.footer.set_xalign(0)
        self.footer.get_style_context().add_class('footer')
        footer_box.pack_start(self.footer, True, True, 0)
        self.quit_button = Gtk.Button(label='QUIT')
        self.quit_button.set_size_request(74, 28)
        self.quit_button.get_style_context().add_class('quitbtn')
        self.quit_button.connect('clicked', lambda *_: self.request_quit())
        footer_box.pack_end(self.quit_button, False, False, 0)

        self.system_button = Gtk.Button(label='SYSTEM')
        self.system_button.set_size_request(92, 28)
        self.system_button.get_style_context().add_class('systembtn')
        self.system_button.connect('clicked', lambda *_: self.show_system_menu())
        footer_box.pack_end(self.system_button, False, False, 0)
        footer_overlay.add_overlay(footer_box)
        self.footer_box = footer_overlay
        content.pack_end(footer_overlay, False, False, 0)

        self.rail_buttons = {}
        self.rail_revealer = Gtk.Revealer()
        self.in_rail = False

    def build_home(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        box.set_size_request(696, 454)
        box.set_border_width(1)

        # CRT-safe hero: text and map are two separate columns.
        # This prevents map artwork/text from ever overlapping the status message.
        self.hero = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.hero.set_size_request(690, 154)
        self.hero.get_style_context().add_class('hero')

        controls = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        controls.set_size_request(314, 148)
        controls.set_margin_start(16)
        controls.set_margin_end(8)
        controls.set_margin_top(10)
        controls.set_margin_bottom(8)

        self.hero_title = Gtk.Label(label='SHIELD ARMOR OFFLINE')
        self.hero_title.set_xalign(0)
        self.hero_title.set_line_wrap(False)
        self.hero_title.set_ellipsize(3)
        self.hero_title.get_style_context().add_class('hero-title')
        self.hero_title.get_style_context().add_class('armor-title')
        self.hero_title.get_style_context().add_class('armor-offline')

        self.hero_sub = Gtk.Label(label='Schnell verbinden wählt automatisch den besten Server.')
        self.hero_sub.set_xalign(0)
        self.hero_sub.set_line_wrap(True)
        self.hero_sub.set_max_width_chars(34)
        self.hero_sub.get_style_context().add_class('hero-sub')

        self.hero_action = Gtk.Button(label='SCHNELL VERBINDEN')
        self.hero_action.get_style_context().add_class('primary')
        self.hero_action.set_size_request(214, 44)
        self.hero_action.connect('clicked', lambda *_: self.hero_action_clicked())

        controls.pack_start(self.hero_title, False, False, 0)
        controls.pack_start(self.hero_sub, False, False, 0)
        controls.pack_end(self.hero_action, False, False, 0)
        self.hero.pack_start(controls, False, False, 0)

        map_box = Gtk.Box()
        map_box.set_size_request(356, 154)
        map_box.set_halign(Gtk.Align.END)
        map_box.set_valign(Gtk.Align.FILL)
        if os.path.exists(HERO_MAP):
            try:
                hero_pix = GdkPixbuf.Pixbuf.new_from_file_at_scale(HERO_MAP, 356, 154, False)
                bg = Gtk.Image.new_from_pixbuf(hero_pix)
                bg.set_size_request(356, 154)
                bg.set_halign(Gtk.Align.FILL)
                bg.set_valign(Gtk.Align.FILL)
                map_box.pack_start(bg, True, True, 0)
            except Exception:
                pass
        self.hero.pack_end(map_box, True, True, 0)
        box.pack_start(self.hero, False, False, 0)

        title = Gtk.Label(label='LÄNDER')
        title.set_xalign(0)
        title.set_margin_top(0)
        title.get_style_context().add_class('section')
        box.pack_start(title, False, False, 0)

        self.category_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        self.category_bar.get_style_context().add_class('tabs')
        self.category_buttons = []
        for i, (label, _kind) in enumerate(CATEGORY_GROUPS):
            shown = '★ FAV' if label == 'FAVORITEN' else label
            b = Gtk.Button(label=shown)
            b.get_style_context().add_class('tab')
            b.connect('clicked', lambda _b, n=i: self.set_home_category(n))
            self.category_bar.pack_start(b, True, True, 0)
            self.category_buttons.append(b)
        box.pack_start(self.category_bar, False, False, 0)

        self.home_hint = Gtk.Label(label='')
        self.home_hint.hide()

        self.home_scroll = Gtk.ScrolledWindow()
        self.home_scroll.set_size_request(690, 104)
        self.home_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.NEVER)
        self.home_card_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.home_card_box.set_halign(Gtk.Align.CENTER)
        self.home_card_box.set_valign(Gtk.Align.START)
        self.home_scroll.add(self.home_card_box)
        box.pack_start(self.home_scroll, False, False, 0)

        self.mid_panel = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.mid_panel.set_size_request(690, 88)
        self.mid_panel.set_margin_top(2)
        self.mid_panel.get_style_context().add_class('bandframe')

        band_overlay = Gtk.Overlay()
        band_overlay.set_size_request(690, 88)
        if os.path.exists(BAND_ART):
            try:
                band_pix = GdkPixbuf.Pixbuf.new_from_file_at_scale(BAND_ART, 690, 88, False)
                band = Gtk.Image.new_from_pixbuf(band_pix)
                band.set_size_request(690, 88)
                band_overlay.add(band)
            except Exception:
                pass

        center = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        center.set_halign(Gtk.Align.CENTER)
        center.set_valign(Gtk.Align.CENTER)
        center.set_size_request(360, 64)

        self.secure_title = Gtk.Label(label='SHIELD VPN SECURE SYSTEM')
        self.secure_title.set_xalign(0.5)
        self.secure_title.get_style_context().add_class('securetitle')
        center.pack_start(self.secure_title, False, False, 0)

        secure_sub = Gtk.Label(label='PRIVACY  //  ENCRYPTED  //  ALWAYS ON')
        secure_sub.set_xalign(0.5)
        secure_sub.get_style_context().add_class('securesub')
        center.pack_start(secure_sub, False, False, 0)

        band_overlay.add_overlay(center)
        self.mid_panel.pack_start(band_overlay, True, True, 0)
        box.pack_start(self.mid_panel, False, False, 0)

        self.stack.add_named(box, 'home')


    def _build_mid_fallback(self):
        self.mid_panel.get_style_context().add_class('midpanel')
        left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        top = Gtk.Label(label='◢─◈─◢')
        top.get_style_context().add_class('midline')
        top.set_xalign(0)
        sub = Gtk.Label(label='shield')
        sub.get_style_context().add_class('midsub')
        sub.set_xalign(0)
        left.pack_start(top, False, False, 0)
        left.pack_start(sub, False, False, 0)
        self.mid_panel.pack_start(left, False, False, 0)

        center = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        title = Gtk.Label(label='SHIELD VPN SECURE SYSTEM')
        title.get_style_context().add_class('midlabel')
        title.set_xalign(0.5)
        subline = Gtk.Label(label='encrypted // always on // secure')
        subline.get_style_context().add_class('midsub')
        subline.set_xalign(0.5)
        center.pack_start(title, False, False, 0)
        center.pack_start(subline, False, False, 0)
        center.set_hexpand(True)
        self.mid_panel.pack_start(center, True, True, 0)

        right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        top = Gtk.Label(label='◣─◈─◣')
        top.get_style_context().add_class('midline')
        top.set_xalign(1)
        sub = Gtk.Label(label='secure')
        sub.get_style_context().add_class('midsub')
        sub.set_xalign(1)
        right.pack_start(top, False, False, 0)
        right.pack_start(sub, False, False, 0)
        self.mid_panel.pack_end(right, False, False, 0)

    def set_home_category(self, idx):
        self.home_category = idx % len(CATEGORY_GROUPS)
        self.home_item_index = 0
        self.home_view_start = 0
        for i, b in enumerate(self.category_buttons):
            ctx = b.get_style_context()
            ctx.remove_class('tabactive')
            if i == self.home_category:
                ctx.add_class('tabactive')
        self.render_home_cards()
        if self.mode == 'home':
            kind = CATEGORY_GROUPS[self.home_category][1]
            self.update_rail_active('favorites' if kind == 'favorites' else 'home')

    def country_code(self, country):
        raw = str(country or '').strip()
        pretty_name = pretty(raw)
        for key in (raw.casefold(), pretty_name.casefold(), tokenise(pretty_name).casefold()):
            code = self.country_codes.get(key, '')
            if code:
                return str(code).upper()
        code = ENGLISH_COUNTRY_CODES.get(pretty_name.casefold(), '')
        return str(code).upper()

    def display_country(self, country):
        code = self.country_code(country)
        if code and code in GERMAN_COUNTRY_NAMES:
            return GERMAN_COUNTRY_NAMES[code]
        return pretty(country)

    def flag_path(self, country):
        code = self.country_code(country).lower()
        if len(code) != 2:
            return ''
        return os.path.join(FLAG_CACHE_DIR, code + '.png')

    def ensure_flag(self, country):
        code = self.country_code(country).lower()
        if len(code) != 2:
            return
        path = os.path.join(FLAG_CACHE_DIR, code + '.png')
        if os.path.exists(path) or code in self.flag_pending:
            return
        self.flag_pending.add(code)
        def worker():
            ok = False
            try:
                url = FLAG_CDN.format(code=code)
                req = urllib.request.Request(url, headers={'User-Agent':'ShieldNordVPN/10.22'})
                with urllib.request.urlopen(req, timeout=10) as r:
                    data = r.read()
                if data:
                    tmp = path + '.tmp'
                    with open(tmp, 'wb') as f:
                        f.write(data)
                    os.replace(tmp, path)
                    ok = True
            except Exception:
                pass
            GLib.idle_add(self.flag_ready, code, ok)
        threading.Thread(target=worker, daemon=True).start()

    def flag_ready(self, code, ok):
        self.flag_pending.discard(code)
        if ok and self.mode == 'home':
            self.render_home_cards(keep_focus=True)
        elif ok and self.mode == 'country' and self.country_tab == 'cities':
            self.render_cities()
        return False

    def _city_slug(self, city):
        text = pretty(city).casefold()
        text = re.sub(r'[^a-z0-9äöüß]+', '-', text, flags=re.I).strip('-')
        return text or 'city'

    def city_flag_cache_path(self, country, city):
        code = self.country_code(country).lower() or 'xx'
        return os.path.join(CITY_FLAG_CACHE_DIR, f'{code}-{self._city_slug(city)}.png')

    def city_flag_asset_path(self, country, city):
        code = self.country_code(country).lower() or 'xx'
        return os.path.join(CITY_FLAG_ASSET_DIR, f'{code}-{self._city_slug(city)}.png')

    def city_flag_display_path(self, country, city):
        for path in (
            self.city_flag_cache_path(country, city),
            self.city_flag_asset_path(country, city),
            self.flag_path(country),
        ):
            if path and os.path.exists(path):
                return path
        return ''

    def _web_json(self, base, params, timeout=10):
        url = base + '?' + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={
            'User-Agent': 'ShieldNordVPN/10.23 (Shield Pi CRT; launcher-size city/server cards)',
            'Accept': 'application/json',
        })
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode('utf-8', errors='replace'))

    @staticmethod
    def _claim_entity_id(entity, prop):
        try:
            claims = entity.get('claims', {}).get(prop, [])
            if not claims:
                return ''
            return claims[0]['mainsnak']['datavalue']['value']['id']
        except Exception:
            return ''

    @staticmethod
    def _claim_commons_filename(entity, prop='P41'):
        try:
            claims = entity.get('claims', {}).get(prop, [])
            if not claims:
                return ''
            value = claims[0]['mainsnak']['datavalue']['value']
            return str(value or '').strip()
        except Exception:
            return ''

    def _wikidata_country_qid(self, country):
        code = self.country_code(country).upper()
        if code in self.wikidata_country_qids:
            return self.wikidata_country_qids[code]
        name = self.display_country(country)
        for lang in ('de', 'en'):
            try:
                data = self._web_json(WIKIDATA_API, {
                    'action':'wbsearchentities', 'search':name, 'language':lang,
                    'uselang':lang, 'type':'item', 'limit':5, 'format':'json',
                })
                for item in data.get('search', []):
                    qid = item.get('id', '')
                    desc = (item.get('description') or '').lower()
                    label = (item.get('label') or '').casefold()
                    if qid and (label == name.casefold() or 'country' in desc or 'staat' in desc):
                        self.wikidata_country_qids[code] = qid
                        return qid
            except Exception:
                pass
        return ''

    def _wikidata_entities(self, ids):
        ids = [x for x in ids if x]
        if not ids:
            return {}
        data = self._web_json(WIKIDATA_API, {
            'action':'wbgetentities', 'ids':'|'.join(ids), 'props':'claims|labels',
            'languages':'en|de', 'format':'json',
        })
        return data.get('entities', {})

    def _commons_thumb_url(self, filename):
        if not filename:
            return ''
        try:
            data = self._web_json(COMMONS_API, {
                'action':'query', 'titles':'File:' + filename, 'prop':'imageinfo',
                'iiprop':'url', 'iiurlwidth':360, 'format':'json',
            })
            for page in data.get('query', {}).get('pages', {}).values():
                infos = page.get('imageinfo') or []
                if infos:
                    info = infos[0]
                    return info.get('thumburl') or info.get('url') or ''
        except Exception:
            pass
        return ''

    def _resolve_city_flag_url(self, country, city):
        city_name = pretty(city)
        expected_country = self._wikidata_country_qid(country)
        candidate_ids = []
        for lang in ('en', 'de'):
            try:
                data = self._web_json(WIKIDATA_API, {
                    'action':'wbsearchentities', 'search':city_name, 'language':lang,
                    'uselang':lang, 'type':'item', 'limit':10, 'format':'json',
                })
                for item in data.get('search', []):
                    qid = item.get('id', '')
                    if qid and qid not in candidate_ids:
                        candidate_ids.append(qid)
            except Exception:
                pass
        entities = self._wikidata_entities(candidate_ids[:10])
        chosen = None
        # Prefer a city entity whose country matches the selected NordVPN country.
        for qid in candidate_ids:
            ent = entities.get(qid, {})
            p17 = self._claim_entity_id(ent, 'P17')
            if expected_country and p17 == expected_country:
                chosen = ent
                break
        if chosen is None:
            for qid in candidate_ids:
                ent = entities.get(qid, {})
                if self._claim_commons_filename(ent, 'P41'):
                    chosen = ent
                    break
        if chosen is None and candidate_ids:
            chosen = entities.get(candidate_ids[0], {})
        if not chosen:
            return ''

        # 1) City flag directly.
        filename = self._claim_commons_filename(chosen, 'P41')
        if filename:
            return self._commons_thumb_url(filename)

        # 2) Administrative-region / state / province flag, walking upward a few levels.
        parent_qid = self._claim_entity_id(chosen, 'P131')
        visited = set()
        for _ in range(4):
            if not parent_qid or parent_qid in visited:
                break
            visited.add(parent_qid)
            parent = self._wikidata_entities([parent_qid]).get(parent_qid, {})
            filename = self._claim_commons_filename(parent, 'P41')
            if filename:
                return self._commons_thumb_url(filename)
            parent_qid = self._claim_entity_id(parent, 'P131')
        return ''

    def ensure_city_flag(self, country, city):
        key = (self.country_code(country).upper(), self._city_slug(city))
        cache = self.city_flag_cache_path(country, city)
        asset = self.city_flag_asset_path(country, city)
        marker = cache + '.fallback'
        if os.path.exists(cache) or os.path.exists(asset) or os.path.exists(marker):
            return
        if key in self.city_flag_pending or key in self.city_flag_failed:
            return
        self.city_flag_pending.add(key)

        def worker():
            ok = False
            try:
                url = self._resolve_city_flag_url(country, city)
                if url:
                    req = urllib.request.Request(url, headers={'User-Agent':'ShieldNordVPN/10.22'})
                    with urllib.request.urlopen(req, timeout=12) as r:
                        data = r.read()
                    if data:
                        tmp = cache + '.tmp'
                        with open(tmp, 'wb') as f:
                            f.write(data)
                        os.replace(tmp, cache)
                        ok = True
            except Exception:
                ok = False
            if not ok:
                try:
                    Path(marker).touch()
                except Exception:
                    pass
            GLib.idle_add(self.city_flag_ready, key, ok)

        threading.Thread(target=worker, daemon=True).start()

    def city_flag_ready(self, key, ok):
        self.city_flag_pending.discard(key)
        if not ok:
            self.city_flag_failed.add(key)
        if self.mode == 'country' and self.country_tab == 'cities':
            self.render_cities()
        return False

    def make_city_tile(self, target):
        country = target.get('country', '')
        city = target.get('city', '')
        b = Gtk.Button()
        b.set_size_request(164, 102)
        b.get_style_context().add_class('citycard')

        overlay = Gtk.Overlay()
        overlay.set_size_request(164, 102)
        base = Gtk.Box()
        base.set_size_request(164, 102)
        base.get_style_context().add_class('cityflagbox')

        path = self.city_flag_display_path(country, city)
        if path:
            try:
                pix = GdkPixbuf.Pixbuf.new_from_file_at_scale(path, 164, 102, False)
                img = Gtk.Image.new_from_pixbuf(pix)
                img.set_size_request(164, 102)
                img.set_halign(Gtk.Align.FILL)
                img.set_valign(Gtk.Align.FILL)
                base.pack_start(img, True, True, 0)
            except Exception:
                pass
        else:
            self.ensure_flag(country)
        self.ensure_city_flag(country, city)
        overlay.add(base)

        name_bar = Gtk.Box()
        name_bar.set_size_request(164, 27)
        name_bar.set_halign(Gtk.Align.FILL)
        name_bar.set_valign(Gtk.Align.END)
        name_bar.get_style_context().add_class('citynamebar')
        name = Gtk.Label(label=pretty(city))
        name.set_xalign(0.5)
        name.set_justify(Gtk.Justification.CENTER)
        name.set_ellipsize(3)
        name.set_max_width_chars(18)
        name.get_style_context().add_class('cityname')
        name_bar.pack_start(name, True, True, 0)
        overlay.add_overlay(name_bar)
        b.add(overlay)
        return b

    def make_server_tile(self, target):
        # Concrete server cards use the location flag and the same 164x102 HOME geometry.
        country = target.get('country', '')
        city = target.get('city', '')
        b = Gtk.Button()
        b.set_size_request(164, 102)
        b.get_style_context().add_class('citycard')

        overlay = Gtk.Overlay()
        overlay.set_size_request(164, 102)
        base = Gtk.Box()
        base.set_size_request(164, 102)
        base.get_style_context().add_class('cityflagbox')

        path = self.city_flag_display_path(country, city) if city else self.flag_path(country)
        if path and os.path.exists(path):
            try:
                pix = GdkPixbuf.Pixbuf.new_from_file_at_scale(path, 164, 102, False)
                img = Gtk.Image.new_from_pixbuf(pix)
                img.set_size_request(164, 102)
                img.set_halign(Gtk.Align.FILL)
                img.set_valign(Gtk.Align.FILL)
                base.pack_start(img, True, True, 0)
            except Exception:
                pass
        else:
            self.ensure_flag(country)
        if city:
            self.ensure_city_flag(country, city)
        overlay.add(base)

        host = target.get('server', '').replace('.nordvpn.com', '').upper()
        load = target.get('load')
        badge = Gtk.Box()
        badge.set_halign(Gtk.Align.START)
        badge.set_valign(Gtk.Align.START)
        badge.get_style_context().add_class('serverbadge')
        badge_text = host
        if load is not None:
            badge_text += f'  {load}%'
        badge_lbl = Gtk.Label(label=badge_text)
        badge_lbl.get_style_context().add_class('serverbadge-text')
        badge.pack_start(badge_lbl, False, False, 0)
        overlay.add_overlay(badge)

        name_bar = Gtk.Box()
        name_bar.set_size_request(164, 27)
        name_bar.set_halign(Gtk.Align.FILL)
        name_bar.set_valign(Gtk.Align.END)
        name_bar.get_style_context().add_class('citynamebar')
        label = pretty(city) if city else self.display_country(country)
        name = Gtk.Label(label=label)
        name.set_xalign(0.5)
        name.set_ellipsize(3)
        name.get_style_context().add_class('cityname')
        name_bar.pack_start(name, True, True, 0)
        overlay.add_overlay(name_bar)
        b.add(overlay)
        return b

    def make_preview_city_tile(self, target):
        country = target.get('country', '')
        city = target.get('city', '')
        b = Gtk.Button()
        b.set_size_request(164, 102)
        b.get_style_context().add_class('serverpreview-card')
        overlay = Gtk.Overlay(); overlay.set_size_request(164, 102)
        base = Gtk.Box(); base.set_size_request(164, 102)
        path = self.city_flag_display_path(country, city)
        if path and os.path.exists(path):
            try:
                pix = GdkPixbuf.Pixbuf.new_from_file_at_scale(path, 164, 102, False)
                image = Gtk.Image.new_from_pixbuf(pix)
                image.set_size_request(164, 102)
                base.pack_start(image, True, True, 0)
            except Exception:
                pass
        else:
            self.ensure_flag(country)
        self.ensure_city_flag(country, city)
        overlay.add(base)
        bar = Gtk.Box(); bar.set_size_request(164, 27); bar.set_halign(Gtk.Align.FILL); bar.set_valign(Gtk.Align.END)
        bar.get_style_context().add_class('serverpreview-namebar')
        label = Gtk.Label(label=pretty(city)); label.set_xalign(0.5); label.set_ellipsize(3)
        label.get_style_context().add_class('serverpreview-name')
        bar.pack_start(label, True, True, 0); overlay.add_overlay(bar)
        b.add(overlay)
        return b

    def make_preview_server_tile(self, target):
        country = target.get('country', '')
        city = target.get('city', '')
        b = Gtk.Button(); b.set_size_request(164, 102); b.get_style_context().add_class('serverpreview-card')
        overlay = Gtk.Overlay(); overlay.set_size_request(164, 102)
        base = Gtk.Box(); base.set_size_request(164, 102)
        path = self.city_flag_display_path(country, city) if city else self.flag_path(country)
        if path and os.path.exists(path):
            try:
                pix = GdkPixbuf.Pixbuf.new_from_file_at_scale(path, 164, 102, False)
                image = Gtk.Image.new_from_pixbuf(pix); image.set_size_request(164, 102)
                base.pack_start(image, True, True, 0)
            except Exception:
                pass
        else:
            self.ensure_flag(country)
        if city: self.ensure_city_flag(country, city)
        overlay.add(base)
        host = target.get('server', '').replace('.nordvpn.com', '').upper()
        load = target.get('load')
        badge = Gtk.Label(label=(host + (f'  {load}%' if load is not None else '')))
        badge.set_halign(Gtk.Align.START); badge.set_valign(Gtk.Align.START)
        badge.get_style_context().add_class('serverpreview-badge'); overlay.add_overlay(badge)
        bar = Gtk.Box(); bar.set_size_request(164, 27); bar.set_halign(Gtk.Align.FILL); bar.set_valign(Gtk.Align.END)
        bar.get_style_context().add_class('serverpreview-namebar')
        label = Gtk.Label(label=pretty(city) if city else self.display_country(country)); label.set_xalign(0.5); label.set_ellipsize(3)
        label.get_style_context().add_class('serverpreview-name')
        bar.pack_start(label, True, True, 0); overlay.add_overlay(bar)
        b.add(overlay)
        return b

    def home_items_for_category(self):
        label, kind = CATEGORY_GROUPS[self.home_category]
        items = []
        if kind == 'recent':
            items = [dict(x) for x in self.recent]
        elif kind == 'favorites':
            items = [dict(x) for x in self.favorites]
        else:
            start, end = kind
            for c in self.countries:
                name = self.display_country(c)
                initial = alpha_initial(name)
                if initial and start <= initial <= end:
                    items.append({'type': 'country', 'country': c})
            items.sort(key=lambda x: self.display_country(x.get('country')).casefold())
        return items

    def make_country_tile(self, target):
        country = target.get('country', '')
        b = Gtk.Button()
        # Exact dimensions from the launcher's original top application row.
        b.set_size_request(164, 102)
        b.get_style_context().add_class('countrycard')

        overlay = Gtk.Overlay()
        overlay.set_size_request(164, 102)

        # Launcher-style country card: same rectangular geometry as the top app row.
        # The flag fills the tile, with the country name overlaid at the bottom.
        base = Gtk.Box()
        base.set_size_request(164, 102)
        base.get_style_context().add_class('countryflagbox')

        path = self.flag_path(country)
        if path and os.path.exists(path):
            try:
                pix = GdkPixbuf.Pixbuf.new_from_file_at_scale(path, 164, 102, False)
                img = Gtk.Image.new_from_pixbuf(pix)
                img.set_size_request(164, 102)
                img.set_halign(Gtk.Align.FILL)
                img.set_valign(Gtk.Align.FILL)
                base.pack_start(img, True, True, 0)
            except Exception:
                pass
        else:
            self.ensure_flag(country)

        overlay.add(base)

        name_bar = Gtk.Box()
        name_bar.set_size_request(164, 27)
        name_bar.set_halign(Gtk.Align.FILL)
        name_bar.set_valign(Gtk.Align.END)
        name_bar.get_style_context().add_class('countrynamebar')

        name = Gtk.Label(label=self.display_country(country))
        name.set_xalign(0.5)
        name.set_justify(Gtk.Justification.CENTER)
        name.set_ellipsize(3)
        name.set_max_width_chars(18)
        name.get_style_context().add_class('countryname')
        name_bar.pack_start(name, True, True, 0)
        overlay.add_overlay(name_bar)

        b.add(overlay)
        return b

    def make_generic_home_tile(self, target):
        b = Gtk.Button(label=self.target_label(target))
        b.set_size_request(164, 102)
        b.get_style_context().add_class('citycard')
        return b

    def normalize_home_carousel(self):
        n = len(self.home_items)
        if n <= 0:
            self.home_item_index = 0
            self.home_view_start = 0
            return
        self.home_item_index = max(0, min(self.home_item_index, n - 1))
        if self.home_item_index < self.home_view_start:
            self.home_view_start = self.home_item_index
        elif self.home_item_index >= self.home_view_start + self.home_visible_count:
            self.home_view_start = self.home_item_index - self.home_visible_count + 1
        self.home_view_start = max(
            0,
            min(self.home_view_start, max(0, n - self.home_visible_count))
        )

    def render_home_cards(self, keep_focus=False):
        old_focus_row = self.nav_row
        self.home_items = self.home_items_for_category()
        self.normalize_home_carousel()

        for child in self.home_card_box.get_children():
            self.home_card_box.remove(child)

        widgets = []
        if not self.home_items:
            l = Gtk.Label(label='Keine Einträge in diesem Bereich.')
            l.get_style_context().add_class('muted')
            self.home_card_box.pack_start(l, False, False, 10)
        else:
            visible = self.home_items[
                self.home_view_start:self.home_view_start + self.home_visible_count
            ]
            for target in visible:
                typ = target.get('type')
                if typ == 'country':
                    b = self.make_country_tile(target)
                else:
                    b = self.make_generic_home_tile(target)
                b.connect('clicked', lambda _b, t=dict(target): self.short_activate_target(t))
                self.home_card_box.pack_start(b, False, False, 0)
                widgets.append(b)
                self.widget_targets[b] = dict(target)

        self.home_card_box.show_all()
        self.set_nav_rows(
            [[self.hero_action], list(self.category_buttons), widgets],
            focus_first=False
        )

        if self.mode == 'home' and widgets and not self.in_rail:
            self.nav_row = 2 if keep_focus or old_focus_row == 2 else old_focus_row
            if self.nav_row == 2:
                local = self.home_item_index - self.home_view_start
                self.nav_col = max(0, min(local, len(widgets)-1))
                GLib.idle_add(widgets[self.nav_col].grab_focus)

    def move_home_carousel(self, delta):
        if not self.home_items:
            return
        new_index = self.home_item_index + delta
        if new_index < 0 or new_index >= len(self.home_items):
            return
        self.home_item_index = new_index
        self.render_home_cards(keep_focus=True)

    def target_label(self, t):
        typ = t.get('type')
        if typ == 'server':
            host = t.get('server', '').replace('.nordvpn.com', '')
            city = pretty(t.get('city', ''))
            load = t.get('load')
            second = city.upper() if city else 'SERVER'
            if load is not None:
                second += f'   LAST {load}%'
            return f'{host.upper()}\n{second}'
        country = self.display_country(t.get('country', '')).upper()
        city = pretty(t.get('city', '')).upper()
        if typ == 'city' and city:
            return f'{city}\n{country}'
        return country or 'UNBEKANNT'

    def short_activate_target(self, target):
        self.connect_target(target)

    def open_target_from_home(self, target):
        self.short_activate_target(target)

    def _set_country_page_geometry(self, active):
        """Keep the SHIELD SERVER GRID page at its native CRT geometry.

        The country preview is a fixed 696x522 canvas.  When the normal top/footer
        are hidden we must stop Gtk.Stack from squeezing the canvas into its
        normal 454 px slot, otherwise the title/info/card/band zones overlap.
        """
        if active:
            self.stack.set_size_request(696, 522)
            self.stack.set_vexpand(False)
            self.stack.set_valign(Gtk.Align.START)
        else:
            self.stack.set_size_request(696, 454)
            self.stack.set_vexpand(True)
            self.stack.set_valign(Gtk.Align.FILL)
        self.stack.queue_resize()

    def build_country_detail(self):
        # Full approved SHIELD SERVER GRID preview as the actual skin.
        # This page hides the normal top/footer so the 4:3 artwork can keep its exact proportions.
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        box.set_size_request(696, 522)
        box.set_halign(Gtk.Align.START)
        box.set_valign(Gtk.Align.START)
        box.set_hexpand(False)
        box.set_vexpand(False)
        box.get_style_context().add_class('countrypage')

        overlay = Gtk.Overlay()
        overlay.set_size_request(696, 522)
        overlay.set_halign(Gtk.Align.START)
        overlay.set_valign(Gtk.Align.START)
        overlay.set_hexpand(False)
        overlay.set_vexpand(False)
        if os.path.exists(COUNTRY_PREVIEW_BG):
            try:
                pix = GdkPixbuf.Pixbuf.new_from_file_at_scale(COUNTRY_PREVIEW_BG, 696, 522, False)
                bg = Gtk.Image.new_from_pixbuf(pix)
                bg.set_size_request(696, 522)
                bg.set_halign(Gtk.Align.START)
                bg.set_valign(Gtk.Align.START)
            except Exception:
                bg = Gtk.Label(label='SHIELD SERVER GRID')
        else:
            bg = Gtk.Label(label='SHIELD SERVER GRID')
        overlay.add(bg)

        fixed = Gtk.Fixed()
        fixed.set_size_request(696, 522)
        fixed.set_halign(Gtk.Align.START)
        fixed.set_valign(Gtk.Align.START)
        overlay.add_overlay(fixed)

        # Live top status replaces the static data from the preview.
        self.country_top_status = Gtk.Label(label='PROTOCOL: -   |   IP: -   |   LOCATION: -   |   TIME: -')
        self.country_top_status.set_xalign(1)
        self.country_top_status.set_size_request(500, 24)
        self.country_top_status.get_style_context().add_class('serverpreview-live')
        fixed.put(self.country_top_status, 166, 18)

        # Dynamic country title and subtitle exactly over the preview title zone.
        self.country_title = Gtk.Label(label='LAND')
        self.country_title.set_xalign(0)
        self.country_title.set_size_request(345, 28)
        self.country_title.get_style_context().add_class('serverpreview-title')
        fixed.put(self.country_title, 31, 68)

        self.country_subtitle = Gtk.Label(label='Server-Standort auswählen')
        self.country_subtitle.set_xalign(0)
        self.country_subtitle.set_size_request(345, 17)
        self.country_subtitle.get_style_context().add_class('serverpreview-sub')
        fixed.put(self.country_subtitle, 31, 99)

        self.country_summary = Gtk.Label(label='LAND  //  STANDORTE  //  SERVER')
        self.country_summary.set_xalign(0)
        self.country_summary.set_size_request(425, 21)
        self.country_summary.get_style_context().add_class('serverpreview-info')
        fixed.put(self.country_summary, 78, 139)

        # Minimal Cities / Servers switch in the information strip.
        self.tab_cities = Gtk.Button(label='STÄDTE')
        self.tab_servers = Gtk.Button(label='SERVER')
        for b in (self.tab_cities, self.tab_servers):
            b.get_style_context().add_class('serverpreview-tab')
            b.set_size_request(76, 24)
        self.tab_cities.connect('clicked', lambda *_: self.set_country_tab('cities'))
        self.tab_servers.connect('clicked', lambda *_: self.set_country_tab('servers'))
        fixed.put(self.tab_cities, 511, 137)
        fixed.put(self.tab_servers, 591, 137)

        # Hidden compatibility controls: country favorite / quick connect remain available in code
        # but the approved preview uses direct OK / long-OK on the location cards instead.
        self.country_quick = Gtk.Button(label='SCHNELLSTER SERVER')
        self.country_fav = Gtk.Button(label='☆ FAVORIT')
        self.country_quick.connect('clicked', lambda *_: self.connect_country())
        self.country_fav.connect('clicked', lambda *_: self.toggle_country_favorite())
        self.country_quick.hide(); self.country_fav.hide()

        self.country_note = Gtk.Label(label='')
        self.country_note.hide()

        # Four exact-preview location slots. Carousel swaps only these four live cards.
        self.country_card_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.country_card_box.set_size_request(680, 102)
        self.country_card_box.set_halign(Gtk.Align.START)
        self.country_card_box.set_valign(Gtk.Align.START)
        fixed.put(self.country_card_box, 8, 201)
        self.country_scroll = None

        # Live footer actions inside the exact preview skin.
        self.country_system_button = Gtk.Button(label='SYSTEM')
        self.country_system_button.set_size_request(78, 30)
        self.country_system_button.get_style_context().add_class('serverpreview-footerbtn')
        self.country_system_button.connect('clicked', lambda *_: self.show_system_menu())
        fixed.put(self.country_system_button, 515, 442)

        self.country_quit_button = Gtk.Button(label='QUIT')
        self.country_quit_button.set_size_request(78, 30)
        self.country_quit_button.get_style_context().add_class('quitbtn')
        self.country_quit_button.connect('clicked', lambda *_: self.request_quit())
        fixed.put(self.country_quit_button, 600, 442)

        box.pack_start(overlay, True, True, 0)
        self.stack.add_named(box, 'country')

    def open_country(self, country, initial_city=None):
        previous = self.selected_country
        new_country = previous != country
        self.mode = 'country'
        self.selected_country = country
        if new_country:
            self.country_city_index = 0
            self.country_city_view_start = 0
            self.country_server_index = 0
            self.country_server_view_start = 0
            self.country_cities = []
            self.country_servers = []
        self.country_title.set_text(self.display_country(country).upper())
        self.country_subtitle.set_text('SERVER-STANDORT AUSWÄHLEN // SHIELD NODE NETWORK')
        self.update_country_fav_button()
        if hasattr(self, 'top_bar'): self.top_bar.hide()
        if hasattr(self, 'footer_box'): self.footer_box.hide()
        self._set_country_page_geometry(True)
        self.stack.set_visible_child_name('country')
        self.update_rail_active(None)
        self.country_tab = 'cities'
        self.set_country_tab('cities')
        self.clear_country_grid()
        self.set_nav_rows([[self.tab_cities, self.tab_servers], [self.country_system_button, self.country_quit_button]])
        self.load_country_cities(country, initial_city)
        self.load_country_servers(country)
        if hasattr(self, 'footer'):
            self.footer.set_text('← → Standort    OK verbinden    OK halten Details')

    def return_to_country_detail(self):
        self.mode = 'country'
        if hasattr(self, 'top_bar'): self.top_bar.hide()
        if hasattr(self, 'footer_box'): self.footer_box.hide()
        self._set_country_page_geometry(True)
        self.stack.set_visible_child_name('country')
        self.update_rail_active(None)
        self.set_country_tab(self.country_detail_return_tab, keep_focus=True)

    def update_country_grid_summary(self):
        if not hasattr(self, 'country_summary'):
            return
        city_count = len(getattr(self, 'country_cities', []) or [])
        server_count = len(getattr(self, 'country_servers', []) or [])
        country_name = self.display_country(self.selected_country) if self.selected_country else 'LAND'
        self.country_summary.set_text(
            f'{country_name.upper()}  //  {server_count or city_count} SERVER  //  {city_count} STANDORTE VERFÜGBAR'
        )

    def clear_country_grid(self):
        for child in self.country_card_box.get_children():
            self.country_card_box.remove(child)

    def set_country_tab(self, which, keep_focus=False):
        self.country_tab = which
        for b, name in ((self.tab_cities, 'cities'), (self.tab_servers, 'servers')):
            ctx = b.get_style_context()
            ctx.remove_class('tabactive')
            if name == which:
                ctx.add_class('tabactive')
        if which == 'cities':
            self.render_cities(keep_focus=keep_focus)
        else:
            self.render_servers(keep_focus=keep_focus)

    def load_country_cities(self, country, initial_city=None):
        self.country_cities = []
        def worker():
            rc, out = run_cmd(['nordvpn', 'cities', country])
            cities = parse_tokens(out) if rc == 0 else []
            cities = sorted(set(cities), key=lambda x: pretty(x).casefold())
            GLib.idle_add(self.finish_cities, country, cities, initial_city)
        threading.Thread(target=worker, daemon=True).start()

    def finish_cities(self, country, cities, initial_city):
        if self.selected_country != country:
            return False
        self.country_cities = cities
        self.update_country_grid_summary()
        if initial_city:
            wanted = tokenise(initial_city).casefold()
            for i, city in enumerate(cities):
                if tokenise(city).casefold() == wanted:
                    self.country_city_index = i
                    break
        self._normalize_country_carousel('cities')
        if self.country_tab == 'cities':
            self.render_cities(keep_focus=bool(initial_city))
        return False

    def load_country_servers(self, country):
        self.country_servers = []
        self.country_note.set_text('STÄDTE VIA NORDVPN // SERVER GRID WIRD SYNCHRONISIERT')

        def worker():
            servers = []
            err = ''
            try:
                if not self.country_ids:
                    data = api_json(API_COUNTRIES)
                    for item in data:
                        name = item.get('name', '')
                        cid = item.get('id')
                        code = item.get('code', '')
                        if name and cid is not None:
                            self.country_ids[name.casefold()] = cid
                        if code and cid is not None:
                            self.country_ids[code.casefold()] = cid
                pname = pretty(country)
                cid = self.country_ids.get(pname.casefold())
                if cid is None:
                    for k, v in self.country_ids.items():
                        if k.replace(' ', '') == pname.casefold().replace(' ', ''):
                            cid = v
                            break
                if cid is None:
                    raise RuntimeError('Land nicht in NordVPN-API gefunden')
                params = urllib.parse.urlencode({'filters[country_id]': cid, 'limit': 18})
                data = api_json(API_RECOMMEND + '?' + params)
                for item in data:
                    host = item.get('hostname', '')
                    if not host:
                        continue
                    city = ''
                    try:
                        city = item['locations'][0]['country']['city']['name']
                    except Exception:
                        pass
                    servers.append({
                        'type': 'server',
                        'country': country,
                        'city': tokenise(city),
                        'server': host,
                        'load': item.get('load'),
                    })
            except Exception as e:
                err = str(e)
            GLib.idle_add(self.finish_servers, country, servers, err)
        threading.Thread(target=worker, daemon=True).start()

    def finish_servers(self, country, servers, err):
        if self.selected_country != country:
            return False
        self.country_servers = servers
        self.server_error = err
        self.update_country_grid_summary()
        self._normalize_country_carousel('servers')
        if self.country_tab == 'servers':
            self.render_servers()
        return False

    def _country_targets(self, which=None):
        which = which or self.country_tab
        if which == 'cities':
            return [
                {'type': 'city', 'country': self.selected_country, 'city': city}
                for city in getattr(self, 'country_cities', [])
            ]
        return [dict(t) for t in getattr(self, 'country_servers', [])]

    def _country_index_state(self, which=None):
        which = which or self.country_tab
        if which == 'cities':
            return self.country_city_index, self.country_city_view_start
        return self.country_server_index, self.country_server_view_start

    def _set_country_index_state(self, which, index, view_start):
        if which == 'cities':
            self.country_city_index = index
            self.country_city_view_start = view_start
        else:
            self.country_server_index = index
            self.country_server_view_start = view_start

    def _normalize_country_carousel(self, which=None):
        which = which or self.country_tab
        items = self._country_targets(which)
        index, view = self._country_index_state(which)
        if not items:
            self._set_country_index_state(which, 0, 0)
            return
        index = max(0, min(index, len(items) - 1))
        if index < view:
            view = index
        elif index >= view + self.country_visible_count:
            view = index - self.country_visible_count + 1
        view = max(0, min(view, max(0, len(items) - self.country_visible_count)))
        self._set_country_index_state(which, index, view)

    def render_country_carousel(self, which, keep_focus=False):
        if self.mode != 'country' or self.country_tab != which:
            return
        self.clear_country_grid()
        self._normalize_country_carousel(which)
        items = self._country_targets(which)
        index, view = self._country_index_state(which)
        widgets = []

        if items:
            visible = items[view:view + self.country_visible_count]
            for target in visible:
                if which == 'cities':
                    b = self.make_preview_city_tile(target)
                else:
                    b = self.make_preview_server_tile(target)
                b.connect('clicked', lambda _b, t=dict(target): self.short_activate_target(t))
                self.country_card_box.pack_start(b, False, False, 0)
                widgets.append(b)
                self.widget_targets[b] = dict(target)
        else:
            msg = 'KEINE EINZELNEN STÄDTE GEMELDET // SCHNELLSTEN SERVER NUTZEN'
            if which == 'servers':
                msg = 'SERVER GRID WIRD GELADEN ...'
                if getattr(self, 'server_error', ''):
                    msg = 'SERVER GRID NICHT VERFÜGBAR // STÄDTE BLEIBEN VERFÜGBAR'
            l = Gtk.Label(label=msg)
            l.get_style_context().add_class('countrynote')
            self.country_card_box.pack_start(l, False, False, 8)

        self.country_card_box.show_all()
        self.set_nav_rows(
            [[self.tab_cities, self.tab_servers], widgets, [self.country_system_button, self.country_quit_button]],
            focus_first=False
        )
        if widgets and keep_focus:
            self.nav_row = 1
            local = index - view
            self.nav_col = max(0, min(local, len(widgets)-1))
            GLib.idle_add(widgets[self.nav_col].grab_focus)

    def render_cities(self, keep_focus=False):
        self.render_country_carousel('cities', keep_focus=keep_focus)

    def render_servers(self, keep_focus=False):
        self.render_country_carousel('servers', keep_focus=keep_focus)

    def move_country_carousel(self, delta):
        which = self.country_tab
        items = self._country_targets(which)
        if not items:
            return
        index, view = self._country_index_state(which)
        new_index = index + delta
        if new_index < 0 or new_index >= len(items):
            return
        self._set_country_index_state(which, new_index, view)
        self.render_country_carousel(which, keep_focus=True)

    def open_city_action(self, target):
        # City cards connect immediately, mirroring the TV app's location cards.
        self.connect_target(target)

    # ---------------- server detail/favorite ----------------
    def build_server_detail(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        box.set_border_width(7)
        self.server_title = Gtk.Label(label='SERVER')
        self.server_title.set_xalign(0)
        self.server_title.get_style_context().add_class('section')
        self.server_sub = Gtk.Label(label='')
        self.server_sub.set_xalign(0)
        self.server_sub.get_style_context().add_class('muted')
        self.server_connect = Gtk.Button(label='VERBINDEN')
        self.server_connect.get_style_context().add_class('primary')
        self.server_connect.connect('clicked', lambda *_: self.connect_selected_server())
        self.server_fav = Gtk.Button(label='☆ FAVORIT HINZUFÜGEN')
        self.server_fav.connect('clicked', lambda *_: self.toggle_server_favorite())
        back = Gtk.Button(label='ZURÜCK')
        back.connect('clicked', lambda *_: self.return_to_country_detail())
        for w in (self.server_title, self.server_sub, self.server_connect, self.server_fav, back):
            if isinstance(w, Gtk.Label):
                box.pack_start(w, False, False, 0)
            else:
                box.pack_start(w, False, False, 0)
        self.server_back = back
        self.stack.add_named(box, 'server')

    def open_server(self, target):
        self.mode = 'server'
        self.selected_server = dict(target)
        self.country_detail_return_tab = self.country_tab
        typ = target.get('type')
        city = pretty(target.get('city', ''))
        country = self.display_country(target.get('country', ''))
        load = target.get('load')
        if typ == 'city':
            self.server_title.set_text(city.upper() or 'STANDORT')
            self.server_sub.set_text(f'{country}    //    SHIELD LOCATION NODE')
            self.server_connect.set_label('MIT STANDORT VERBINDEN')
        else:
            host = target.get('server', '').replace('.nordvpn.com', '')
            self.server_title.set_text(host.upper() or 'SERVER')
            sub = ' / '.join(x for x in (country, city) if x)
            if load is not None:
                sub += f'    LAST {load}%'
            self.server_sub.set_text(sub)
            self.server_connect.set_label('MIT SERVER VERBINDEN')
        self.update_server_fav_button()
        self.stack.set_visible_child_name('server')
        self.update_rail_active(None)
        if hasattr(self, 'footer'):
            self.footer.set_text('OK verbinden    ★ Favorit    ↩ Zurück')
        self.set_nav_rows([[self.server_connect], [self.server_fav], [self.server_back]])

    # ---------------- favorites / recent ----------------
    def fav_key(self, t):
        typ = t.get('type')
        if typ == 'server':
            return ('server', t.get('server', ''))
        if typ == 'city':
            return ('city', t.get('country', ''), t.get('city', ''))
        return ('country', t.get('country', ''))

    def is_favorite(self, t):
        key = self.fav_key(t)
        return any(self.fav_key(x) == key for x in self.favorites if isinstance(x, dict))

    def toggle_favorite(self, t):
        key = self.fav_key(t)
        if self.is_favorite(t):
            self.favorites = [x for x in self.favorites if self.fav_key(x) != key]
        else:
            self.favorites.insert(0, dict(t))
        self.favorites = self.favorites[:40]
        write_json_file(FAV_FILE, self.favorites)
        if self.mode == 'home' and CATEGORY_GROUPS[self.home_category][1] == 'favorites':
            self.render_home_cards()

    def add_recent(self, target):
        if not target:
            return
        key = self.fav_key(target)
        self.recent = [x for x in self.recent if self.fav_key(x) != key]
        self.recent.insert(0, dict(target))
        self.recent = self.recent[:18]
        write_json_file(RECENT_FILE, self.recent)

    def toggle_country_favorite(self):
        if not self.selected_country:
            return
        self.toggle_favorite({'type': 'country', 'country': self.selected_country})
        self.update_country_fav_button()

    def update_country_fav_button(self):
        t = {'type': 'country', 'country': self.selected_country}
        self.country_fav.set_label('★ FAVORIT ENTFERNEN' if self.is_favorite(t) else '☆ FAVORIT')

    def toggle_server_favorite(self):
        if not self.selected_server:
            return
        self.toggle_favorite(self.selected_server)
        self.update_server_fav_button()

    def update_server_fav_button(self):
        self.server_fav.set_label(
            '★ FAVORIT ENTFERNEN' if self.is_favorite(self.selected_server or {}) else '☆ FAVORIT HINZUFÜGEN'
        )

    def _preview_secure_strip(self, title='SHIELD SECURE SYSTEM'):
        strip = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        strip.set_size_request(-1, 32)
        strip.get_style_context().add_class('systemstrip')
        lbl = Gtk.Label(label='◇  ' + title + '  ◇')
        lbl.set_xalign(0.5)
        lbl.get_style_context().add_class('systemstrip-title')
        strip.pack_start(lbl, True, True, 0)
        return strip

    def _second_page_shell(self, image_path):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        box.set_size_request(720, 576)
        overlay = Gtk.Overlay()
        overlay.set_size_request(720, 576)
        if os.path.exists(image_path):
            try:
                pix = GdkPixbuf.Pixbuf.new_from_file_at_scale(image_path, 720, 576, False)
                bg = Gtk.Image.new_from_pixbuf(pix)
            except Exception:
                bg = Gtk.Label(label='SHIELD SECURE SYSTEM')
        else:
            bg = Gtk.Label(label='SHIELD SECURE SYSTEM')
        overlay.add(bg)
        fixed = Gtk.Fixed()
        overlay.add_overlay(fixed)
        box.pack_start(overlay, True, True, 0)
        return box, fixed

    def _second_hotspot(self, fixed, x, y, w, h, callback):
        b = Gtk.Button(label='')
        b.set_relief(Gtk.ReliefStyle.NONE)
        b.set_size_request(w, h)
        b.get_style_context().add_class('second-hotspot')
        b.connect('clicked', lambda *_: callback())
        fixed.put(b, x, y)
        return b

    def _second_footer_button(self, fixed, x, label, callback, quit_style=False):
        b = Gtk.Button(label=label)
        b.set_size_request(92, 30)
        b.get_style_context().add_class('quitbtn' if quit_style else 'serverpreview-footerbtn')
        b.connect('clicked', lambda *_: callback())
        fixed.put(b, x, 538)
        return b

    def _second_label(self, fixed, x, y, w, h, text='', style='second-value', xalign=1.0):
        lbl = Gtk.Label(label=text)
        lbl.set_size_request(w, h)
        lbl.set_xalign(xalign)
        lbl.set_yalign(0.5)
        lbl.set_ellipsize(3)
        lbl.get_style_context().add_class(style)
        fixed.put(lbl, x, y)
        return lbl

    def _active_protocol_mode(self):
        t = self.settings_data
        tech = self.get_any(t, 'technology').upper()
        proto = self.get_any(t, 'protocol').upper()
        if 'NORDWHISPER' in tech:
            return 'nordwhisper'
        if 'NORDLYNX' in tech:
            return 'nordlynx'
        if 'OPENVPN' in tech:
            return 'openvpn_tcp' if 'TCP' in proto else 'openvpn_udp'
        return 'nordlynx'

    def cycle_protocol(self, delta=1):
        modes = ['nordlynx', 'nordwhisper', 'openvpn_udp', 'openvpn_tcp']
        current = self._active_protocol_mode()
        try:
            i = modes.index(current)
        except ValueError:
            i = 0
        self.set_protocol(modes[(i + delta) % len(modes)])

    def toggle_threat_protection(self):
        current = is_on(self.get_any(self.settings_data, 'threat protection lite'))
        new = 'off' if current else 'on'
        self.run_setting_sequence([['nordvpn', 'set', 'threatprotectionlite', new]], reconnect=False)

    def second_quick_connect(self):
        self.hero_action_clicked()

    def cycle_dns_profile(self, delta=1):
        if self.dns_is_default():
            self.set_dns_fixed()
        else:
            addrs = self.dns_addresses()
            if addrs == list(NORD_DNS):
                self.open_dns_keypad()
            else:
                self.set_dns_auto()

    # ---------------- settings ----------------
    def build_settings(self):
        box, fixed = self._second_page_shell(VPN_PAGE_BG)

        # Live top-bar + values cover the static preview values without changing the artwork.
        self.second_vpn_top = self._second_label(fixed, 205, 11, 490, 30, '', 'second-live', 1.0)
        self.second_vpn_protocol = self._second_label(fixed, 235, 166, 150, 30, '', 'second-value', 1.0)
        self.second_vpn_auto = self._second_label(fixed, 280, 211, 100, 28, '', 'second-value', 1.0)
        self.second_vpn_kill = self._second_label(fixed, 280, 255, 100, 28, '', 'second-value', 1.0)
        self.second_vpn_threat = self._second_label(fixed, 280, 299, 100, 28, '', 'second-value', 1.0)
        self.second_vpn_obf = self._second_label(fixed, 280, 344, 100, 28, 'Aus', 'second-value', 1.0)
        self.second_vpn_quick = self._second_label(fixed, 280, 389, 100, 28, '', 'second-value', 1.0)

        self.proto_cycle = self._second_hotspot(fixed, 38, 158, 375, 49, lambda: self.cycle_protocol(1))
        self.btn_auto = self._second_hotspot(fixed, 38, 207, 375, 43, lambda: self.toggle_setting('autoconnect'))
        self.btn_kill = self._second_hotspot(fixed, 38, 251, 375, 43, lambda: self.toggle_setting('killswitch'))
        self.btn_threat = self._second_hotspot(fixed, 38, 295, 375, 43, lambda: self.toggle_threat_protection())
        self.btn_obfuscated = self._second_hotspot(fixed, 38, 339, 375, 43, lambda: None)
        self.btn_quick = self._second_hotspot(fixed, 38, 383, 375, 43, lambda: self.second_quick_connect())
        self.second_vpn_sy = self._second_footer_button(fixed, 510, 'SYSTEM', lambda: self.show_system_menu())
        self.second_vpn_quit = self._second_footer_button(fixed, 608, 'QUIT', lambda: self.request_quit(), quit_style=True)

        # Compatibility objects expected by existing update logic.
        self.proto_buttons = {m: Gtk.Button() for m in ('nordlynx','nordwhisper','openvpn_tcp','openvpn_udp')}
        self.btn_pq = Gtk.Button()
        self.btn_dns = Gtk.Button()
        self.settings_info = Gtk.Label()
        self.settings_note = Gtk.Label()
        self.settings_widgets = [self.proto_cycle, self.btn_auto, self.btn_kill, self.btn_threat, self.btn_obfuscated, self.btn_quick]
        self.stack.add_named(box, 'settings')

    def build_dns(self):
        box, fixed = self._second_page_shell(DNS_PAGE_BG)
        self.second_dns_top = self._second_label(fixed, 205, 11, 490, 30, '', 'second-live', 1.0)
        self.second_dns_mode = self._second_label(fixed, 275, 166, 110, 30, '', 'second-value', 1.0)
        self.second_dns_ad = self._second_label(fixed, 295, 211, 90, 28, '', 'second-value', 1.0)
        self.second_dns_malware = self._second_label(fixed, 295, 255, 90, 28, '', 'second-value', 1.0)
        self.second_dns_tracker = self._second_label(fixed, 295, 299, 90, 28, '', 'second-value', 1.0)
        self.second_dns_doh = self._second_label(fixed, 295, 344, 90, 28, 'Ein', 'second-value', 1.0)
        self.second_dns_search = self._second_label(fixed, 295, 389, 90, 28, 'Ein', 'second-value', 1.0)

        self.dns_cycle_btn = self._second_hotspot(fixed, 31, 158, 395, 49, lambda: self.cycle_dns_profile(1))
        self.dns_ad_btn = self._second_hotspot(fixed, 31, 207, 395, 43, lambda: self.toggle_threat_protection())
        self.dns_malware_btn = self._second_hotspot(fixed, 31, 251, 395, 43, lambda: self.toggle_threat_protection())
        self.dns_tracker_btn = self._second_hotspot(fixed, 31, 295, 395, 43, lambda: self.toggle_threat_protection())
        self.dns_doh_btn = self._second_hotspot(fixed, 31, 339, 395, 43, lambda: None)
        self.dns_search_btn = self._second_hotspot(fixed, 31, 383, 395, 43, lambda: None)
        self.second_dns_sy = self._second_footer_button(fixed, 510, 'SYSTEM', lambda: self.show_system_menu())
        self.second_dns_quit = self._second_footer_button(fixed, 608, 'QUIT', lambda: self.request_quit(), quit_style=True)

        self.dns_state = Gtk.Label()
        self.dns_auto = Gtk.Button(); self.dns_fixed = Gtk.Button(); self.dns_custom = Gtk.Button()
        self.dns_info = Gtk.Label(); self.dns_note = Gtk.Label()
        self.dns_nav_buttons = [self.dns_cycle_btn, self.dns_ad_btn, self.dns_malware_btn, self.dns_tracker_btn, self.dns_doh_btn, self.dns_search_btn]
        self.stack.add_named(box, 'dns')

    def build_dns_keypad(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        box.set_border_width(8)
        title = Gtk.Label(label='EIGENER DNS')
        title.set_xalign(0)
        title.get_style_context().add_class('section')
        box.pack_start(title, False, False, 0)
        self.dns_display = Gtk.Label(label='')
        self.dns_display.set_xalign(0)
        self.dns_display.get_style_context().add_class('dnsdisplay')
        box.pack_start(self.dns_display, False, False, 0)

        grid = Gtk.Grid()
        grid.set_row_spacing(4)
        grid.set_column_spacing(4)
        grid.set_column_homogeneous(True)
        keys = ['1','2','3','4','5','6','7','8','9','.','0','⌫']
        self.dns_key_buttons = []
        for i, key in enumerate(keys):
            b = Gtk.Button(label=key)
            b.get_style_context().add_class('keypad')
            b.connect('clicked', lambda _b, k=key: self.dns_key(k))
            grid.attach(b, i % 4, i // 4, 1, 1)
            self.dns_key_buttons.append(b)
        box.pack_start(grid, False, False, 0)

        actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        self.dns_next = Gtk.Button(label='NÄCHSTER DNS')
        self.dns_clear = Gtk.Button(label='LEEREN')
        self.dns_save = Gtk.Button(label='SPEICHERN')
        self.dns_cancel = Gtk.Button(label='ABBRECHEN')
        self.dns_next.connect('clicked', lambda *_: self.dns_next_field())
        self.dns_clear.connect('clicked', lambda *_: self.dns_clear_field())
        self.dns_save.connect('clicked', lambda *_: self.save_custom_dns())
        self.dns_cancel.connect('clicked', lambda *_: self.open_dns())
        for b in (self.dns_next, self.dns_clear, self.dns_save, self.dns_cancel):
            actions.pack_start(b, True, True, 0)
        box.pack_start(actions, False, False, 0)
        self.dns_key_note = Gtk.Label(label='')
        self.dns_key_note.set_xalign(0)
        self.dns_key_note.get_style_context().add_class('muted')
        box.pack_end(self.dns_key_note, False, False, 0)
        self.stack.add_named(box, 'dnskey')

    def _exactsys_row(self, parent, key, label, value='-'):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        left = Gtk.Label(label=label)
        left.set_xalign(0)
        left.set_hexpand(True)
        left.get_style_context().add_class('exactsys-row')
        right = Gtk.Label(label=value)
        right.set_xalign(1)
        right.get_style_context().add_class('exactsys-value')
        row.pack_start(left, True, True, 0)
        row.pack_end(right, False, False, 0)
        parent.pack_start(row, False, False, 0)
        line = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        parent.pack_start(line, False, False, 0)
        return right

    def _exactsys_header(self, text):
        head = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        head.get_style_context().add_class('exactsys-headrow')
        dot = Gtk.Label(label='◉')
        dot.get_style_context().add_class('exactsys-good')
        title = Gtk.Label(label=text)
        title.set_xalign(0)
        title.get_style_context().add_class('exactsys-headtext')
        head.pack_start(dot, False, False, 0)
        head.pack_start(title, True, True, 0)
        return head

    def _make_exact_system_tile(self, kind):
        button = Gtk.Button()
        button.get_style_context().add_class('exactsys-tile')
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        root.set_border_width(2)
        refs = {}

        titles = {
            'vpn': 'VPN EINSTELLUNGEN',
            'dns': 'DNS SECURE',
            'status': 'SYSTEM STATUS',
            'home': 'NORDVPN (HOME)',
        }
        root.pack_start(self._exactsys_header(titles[kind]), False, False, 0)

        if kind == 'vpn':
            preview = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
            refs['protocol'] = self._exactsys_row(preview, 'protocol', 'Protokoll', 'OpenVPN (UDP)')
            refs['autoconnect'] = self._exactsys_row(preview, 'autoconnect', 'Auto Connect', 'Ein')
            refs['killswitch'] = self._exactsys_row(preview, 'killswitch', 'Kill Switch', 'Ein')
            refs['cybersec'] = self._exactsys_row(preview, 'cybersec', 'CyberSec', 'Ein')
            refs['obfuscated'] = self._exactsys_row(preview, 'obfuscated', 'Obfuscated Server', 'Aus')
            strip = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
            strip.get_style_context().add_class('exactsys-strip')
            sw = Gtk.Label(label='◉')
            sw.get_style_context().add_class('exactsys-good')
            st = Gtk.Label(label='VERBINDUNG HERSTELLEN')
            st.get_style_context().add_class('exactsys-striptext')
            strip.pack_start(sw, False, False, 0)
            strip.pack_start(st, True, True, 0)
            preview.pack_start(strip, False, False, 3)
            refs['uptime'] = self._exactsys_row(preview, 'uptime', 'Verbunden seit', '00:00:00')
            root.pack_start(preview, True, True, 0)
            icon, title, sub = '◎', 'VPN', 'VERBINDUNG & PROTOKOLL'

        elif kind == 'dns':
            preview = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
            refs['dns'] = self._exactsys_row(preview, 'dns', 'DNS Server', 'NordDNS')
            refs['adblock'] = self._exactsys_row(preview, 'adblock', 'Werbeblocker', 'Ein')
            refs['malware'] = self._exactsys_row(preview, 'malware', 'Malware-Schutz', 'Ein')
            refs['tracker'] = self._exactsys_row(preview, 'tracker', 'Tracker-Blocker', 'Ein')
            refs['doh'] = self._exactsys_row(preview, 'doh', 'DNS over HTTPS', 'Ein')
            refs['search'] = self._exactsys_row(preview, 'search', 'Sichere Suchergebnisse', 'Ein')
            root.pack_start(preview, True, True, 0)
            icon, title, sub = 'DNS', 'DNS SECURE', 'WERBEBLOCKER & SCHUTZ'

        elif kind == 'status':
            preview = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
            refs['state'] = self._exactsys_row(preview, 'state', 'VPN Status', 'Offline')
            refs['country'] = self._exactsys_row(preview, 'country', 'Land', '-')
            refs['ip'] = self._exactsys_row(preview, 'ip', 'IP Adresse', '-')
            refs['protocol'] = self._exactsys_row(preview, 'protocol', 'Protokoll', '-')
            refs['uptime'] = self._exactsys_row(preview, 'uptime', 'Verbindungsdauer', '00:00:00')
            refs['down'] = self._exactsys_row(preview, 'down', 'Daten (Download)', '-')
            refs['up'] = self._exactsys_row(preview, 'up', 'Daten (Upload)', '-')
            meter = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
            bars = Gtk.Label(label='▂▄▆█')
            bars.get_style_context().add_class('exactsys-bars')
            chart = Gtk.Label(label='╱╲__╱╲_╱╲\nStabile Verbindung')
            chart.set_justify(Gtk.Justification.CENTER)
            chart.get_style_context().add_class('exactsys-chart')
            meter.pack_start(bars, False, False, 0)
            meter.pack_start(chart, True, True, 0)
            preview.pack_start(meter, False, False, 2)
            root.pack_start(preview, True, True, 0)
            icon, title, sub = '▮▮▮', 'STATUS', 'SYSTEM INFO & VERBINDUNG'

        else:
            preview = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
            mapframe = Gtk.Box()
            mapframe.get_style_context().add_class('exactsys-mapframe')
            if os.path.exists(HERO_MAP):
                try:
                    pix = GdkPixbuf.Pixbuf.new_from_file_at_scale(HERO_MAP, 142, 76, False)
                    image = Gtk.Image.new_from_pixbuf(pix)
                    mapframe.pack_start(image, True, True, 0)
                except Exception:
                    mapframe.pack_start(Gtk.Label(label='WORLD VPN MAP'), True, True, 0)
            preview.pack_start(mapframe, False, False, 0)
            privacy = Gtk.Label(label='PRIVAT\nSICHER\nFREI\nÜBERALL')
            privacy.set_xalign(1)
            privacy.get_style_context().add_class('exactsys-good')
            preview.pack_start(privacy, False, False, 0)
            countrytitle = Gtk.Label(label='LÄNDER')
            countrytitle.set_xalign(0)
            countrytitle.get_style_context().add_class('exactsys-headtext')
            preview.pack_start(countrytitle, False, False, 0)
            countries = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=3)
            for text in ('DE', 'FR', 'CH', 'USA'):
                c = Gtk.Label(label=text)
                c.get_style_context().add_class('exactsys-country')
                countries.pack_start(c, True, True, 0)
            preview.pack_start(countries, False, False, 0)
            strip = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
            strip.get_style_context().add_class('exactsys-strip')
            globe = Gtk.Label(label='◎')
            globe.get_style_context().add_class('exactsys-good')
            disconnect = Gtk.Label(label='VERBINDUNG TRENNEN')
            disconnect.get_style_context().add_class('exactsys-striptext')
            strip.pack_start(globe, False, False, 0)
            strip.pack_start(disconnect, True, True, 0)
            preview.pack_start(strip, False, False, 0)
            root.pack_start(preview, True, True, 0)
            icon, title, sub = '⌂', 'HOME', 'ZURÜCK ZUM HAUPTMENÜ'
            refs['home'] = privacy

        bottom = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        bigicon = Gtk.Label(label=icon)
        bigicon.get_style_context().add_class('exactsys-icon')
        bigname = Gtk.Label(label=title)
        bigname.get_style_context().add_class('exactsys-bigname')
        bigsub = Gtk.Label(label=sub)
        bigsub.set_line_wrap(True)
        bigsub.set_justify(Gtk.Justification.CENTER)
        bigsub.get_style_context().add_class('exactsys-bigsub')
        bottom.pack_start(bigicon, False, False, 0)
        bottom.pack_start(bigname, False, False, 0)
        bottom.pack_start(bigsub, False, False, 0)
        root.pack_end(bottom, False, False, 0)

        button.add(root)
        return button, refs

    def build_system_menu(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        box.set_size_request(696, 454)

        overlay = Gtk.Overlay()
        overlay.set_size_request(696, 454)

        if os.path.exists(SYSTEM_PAGE_BG):
            try:
                pix = GdkPixbuf.Pixbuf.new_from_file_at_scale(SYSTEM_PAGE_BG, 696, 454, False)
                bg = Gtk.Image.new_from_pixbuf(pix)
            except Exception:
                bg = Gtk.Label(label='SHIELD SYSTEM CONTROL')
        else:
            bg = Gtk.Label(label='SHIELD SYSTEM CONTROL')
        overlay.add(bg)

        fixed = Gtk.Fixed()
        overlay.add_overlay(fixed)

        def hotspot(x, y, w, h, callback):
            btn = Gtk.Button(label='')
            btn.set_relief(Gtk.ReliefStyle.NONE)
            btn.set_can_focus(True)
            btn.set_size_request(w, h)
            btn.get_style_context().add_class('system-overlay-hit')
            btn.connect('clicked', lambda *_: callback())
            fixed.put(btn, x, y)
            return btn

        # Transparent focus/click hotspots aligned to the 4 tiles from the approved preview.
        self.sys_vpn = hotspot(14, 99, 165, 286, lambda: self.show_mode('settings'))
        self.sys_dns = hotspot(186, 99, 165, 286, lambda: self.open_dns())
        self.sys_status = hotspot(358, 99, 164, 286, lambda: self.show_mode('status'))
        self.sys_home = hotspot(528, 99, 154, 286, lambda: self.show_mode('home'))

        box.pack_start(overlay, True, True, 0)
        self.stack.add_named(box, 'systemmenu')

    def show_system_menu(self):
        self.mode = 'systemmenu'
        self._set_country_page_geometry(False)
        if hasattr(self, 'top_bar'): self.top_bar.show()
        if hasattr(self, 'footer_box'): self.footer_box.show()
        self.stack.set_visible_child_name('systemmenu')
        if hasattr(self, 'footer'):
            self.footer.set_text('← → Auswahl    OK Öffnen    ↩ Zurück')
        self.set_nav_rows([[self.sys_vpn, self.sys_dns, self.sys_status, self.sys_home]])

    def update_exact_system_preview(self):
        if not hasattr(self, 'sys_vpn_preview'):
            return
        s = self.status_data
        t = self.settings_data
        connected = self.get_any(s, 'status').lower() == 'connected'
        country = self.get_any(s, 'country')
        ip = self.get_any(s, 'ip') or '-'
        uptime = self.get_any(s, 'uptime', 'connection time', 'connection uptime') or '00:00:00'
        tech = self.get_any(s, 'technology', 'current technology') or self.get_any(t, 'technology')
        proto = self.get_any(s, 'protocol', 'current protocol') or self.get_any(t, 'protocol')
        if tech.upper() == 'OPENVPN' and proto:
            protocol = f'OpenVPN ({proto.upper()})'
        else:
            protocol = tech or proto or '-'

        def val(refs, key, value, good=None):
            w = refs.get(key)
            if not w:
                return
            w.set_text(str(value))
            ctx = w.get_style_context()
            ctx.remove_class('exactsys-good')
            ctx.remove_class('exactsys-bad')
            if good is True:
                ctx.add_class('exactsys-good')
            elif good is False:
                ctx.add_class('exactsys-bad')

        val(self.sys_vpn_preview, 'protocol', protocol)
        val(self.sys_vpn_preview, 'autoconnect', self.get_any(t, 'auto-connect') or '-')
        val(self.sys_vpn_preview, 'killswitch', self.get_any(t, 'kill switch') or '-')
        val(self.sys_vpn_preview, 'cybersec', 'Ein' if self.get_any(t, 'threat protection lite').lower() in ('enabled','on','yes','true') else 'Aus')
        val(self.sys_vpn_preview, 'obfuscated', 'Aus')
        val(self.sys_vpn_preview, 'uptime', uptime)

        dns = self.get_any(t, 'dns') or 'NordDNS'
        val(self.sys_dns_preview, 'dns', dns)
        val(self.sys_dns_preview, 'adblock', 'Ein')
        val(self.sys_dns_preview, 'malware', 'Ein')
        val(self.sys_dns_preview, 'tracker', 'Ein')
        val(self.sys_dns_preview, 'doh', 'Ein')
        val(self.sys_dns_preview, 'search', 'Ein')

        val(self.sys_status_preview, 'state', 'Aktiv' if connected else 'Offline', good=connected)
        val(self.sys_status_preview, 'country', self.display_country(country) if country else '-')
        val(self.sys_status_preview, 'ip', ip)
        val(self.sys_status_preview, 'protocol', protocol)
        val(self.sys_status_preview, 'uptime', uptime)
        val(self.sys_status_preview, 'down', '-')
        val(self.sys_status_preview, 'up', '-')

        home = self.sys_home_preview.get('home')
        if home:
            home.set_text('PRIVAT\nSICHER\nFREI\nÜBERALL' if connected else 'VPN\nOFFLINE')
            ctx = home.get_style_context()
            ctx.remove_class('exactsys-good')
            ctx.remove_class('exactsys-bad')
            ctx.add_class('exactsys-good' if connected else 'exactsys-bad')

    def build_status(self):
        box, fixed = self._second_page_shell(STATUS_PAGE_BG)
        self.second_status_top = self._second_label(fixed, 205, 11, 490, 30, '', 'second-live', 1.0)
        # Values only; labels and graphics remain from approved preview background.
        ys = [165, 202, 240, 278, 316, 354, 392]
        self.second_status_values = []
        for y in ys:
            self.second_status_values.append(self._second_label(fixed, 262, y, 145, 28, '-', 'second-value', 1.0))
        self.second_status_country = self._second_label(fixed, 500, 260, 165, 48, '-', 'second-value', 0.5)
        self.status_refresh = self._second_hotspot(fixed, 30, 150, 390, 330, lambda: self.refresh_all(force=True))
        self.second_status_sy = self._second_footer_button(fixed, 510, 'SYSTEM', lambda: self.show_system_menu())
        self.second_status_quit = self._second_footer_button(fixed, 608, 'QUIT', lambda: self.request_quit(), quit_style=True)
        self.detail = Gtk.Label()
        self.status_country = Gtk.Label()
        self.status_security = Gtk.Label()
        self.stack.add_named(box, 'status')

    # ---------------- load/status ----------------
    def load_countries(self):
        def worker():
            rc, out = run_cmd(['nordvpn', 'countries'])
            countries = parse_tokens(out) if rc == 0 else []
            codes = {}
            ids = {}
            try:
                data = api_json(API_COUNTRIES)
                for item in data:
                    name = str(item.get('name', '')).strip()
                    code = str(item.get('code', '')).strip().upper()
                    cid = item.get('id')
                    if name:
                        codes[name.casefold()] = code
                        codes[tokenise(name).casefold()] = code
                        if cid is not None:
                            ids[name.casefold()] = cid
                            ids[tokenise(name).casefold()] = cid
                    if code:
                        codes[code.casefold()] = code
                        if cid is not None:
                            ids[code.casefold()] = cid
            except Exception:
                pass
            GLib.idle_add(self.finish_load_countries, countries, codes, ids)
        threading.Thread(target=worker, daemon=True).start()
        return False

    def finish_load_countries(self, countries, codes=None, ids=None):
        if codes:
            self.country_codes.update(codes)
        if ids:
            self.country_ids.update(ids)
        self.countries = sorted(set(countries), key=lambda x: self.display_country(x).casefold())
        self.set_home_category(self.home_category)
        return False

    def refresh_all(self, force=False):
        if self.refresh_running:
            return True
        if self.busy and not force:
            return True
        self.refresh_running = True
        def worker():
            _, status = run_cmd(['nordvpn', 'status'])
            _, settings = run_cmd(['nordvpn', 'settings'])
            GLib.idle_add(self.apply_refresh, status, settings)
        threading.Thread(target=worker, daemon=True).start()
        return True

    def get_any(self, data, *names):
        for n in names:
            v = data.get(n.lower(), '')
            if v:
                return v
        return ''

    def set_armor_state(self, state):
        if not hasattr(self, 'hero_title'):
            return False
        ctx = self.hero_title.get_style_context()
        for cls in ('armor-offline', 'armor-arming', 'armor-active'):
            ctx.remove_class(cls)
        if state == 'active':
            self.hero_title.set_text('SHIELD ARMOR ACTIVE')
            self.hero_sub.set_text('SECURE LINK ESTABLISHED // ARMOR ENGAGED')
            ctx.add_class('armor-active')
        elif state == 'arming':
            self.hero_title.set_text('SHIELD ARMOR ARMING')
            self.hero_sub.set_text('ESTABLISHING SECURE TUNNEL...')
            ctx.add_class('armor-arming')
        else:
            self.hero_title.set_text('SHIELD ARMOR OFFLINE')
            self.hero_sub.set_text('SECURE LINK UNAVAILABLE')
            ctx.add_class('armor-offline')
        return False

    def apply_refresh(self, status_text, settings_text):
        self.refresh_running = False
        self.status_data = kv(status_text)
        self.settings_data = kv(settings_text)
        s, t = self.status_data, self.settings_data
        connected = self.get_any(s, 'status').lower() == 'connected'
        country = self.get_any(s, 'country')
        city = self.get_any(s, 'city')
        host = self.get_any(s, 'hostname', 'server')
        ip = self.get_any(s, 'ip') or '-'
        uptime = self.get_any(s, 'uptime', 'connection time', 'connection uptime') or '00:00:00'
        tech = self.get_any(s, 'technology', 'current technology') or self.get_any(t, 'technology')
        proto = self.get_any(s, 'protocol', 'current protocol') or self.get_any(t, 'protocol')
        if tech.upper() == 'OPENVPN' and proto:
            proto_text = f'OpenVPN ({proto.upper()})'
        else:
            proto_text = tech or proto or '-'
        self.top_status.set_text(f'Protokoll: {proto_text}    |    Neue IP: {ip}    |    Verbindungszeit: {uptime}')
        if hasattr(self, 'country_top_status'):
            loc = self.display_country(country) if country else '-'
            self.country_top_status.set_text(f'PROTOCOL: {proto_text}   |   IP: {ip}   |   LOCATION: {loc}   |   TIME: {uptime}')

        if hasattr(self, 'system_state_label'):
            sysctx = self.system_state_label.get_style_context()
            sysctx.remove_class('systemstate-active')
            if connected:
                sysctx.add_class('systemstate-active')
                country_name = self.display_country(country) if country else ''
                suffix = f'  |  {country_name}' if country_name else ''
                self.system_state_label.set_text(f'VPN LINK: ACTIVE  |  {proto_text}{suffix}')
            else:
                self.system_state_label.set_text('VPN LINK: OFFLINE  |  SYSTEM READY')
        if hasattr(self, 'sys_vpn_sub'):
            self.sys_vpn_sub.set_text(f'Aktiv: {proto_text}' if connected else 'NordLynx · NordWhisper · OpenVPN TCP/UDP')

        hctx = self.hero.get_style_context()
        hctx.remove_class('hero-connected')

        if hasattr(self, 'secure_title'):
            sctx = self.secure_title.get_style_context()
            sctx.remove_class('securetitle-active')
            if connected:
                sctx.add_class('securetitle-active')

        status_word = self.get_any(s, 'status').lower()
        if connected:
            hctx.add_class('hero-connected')
            self._armor_pending = False
            self.set_armor_state('active')
            self.hero_action.set_label('TRENNEN')
        elif self._armor_pending or 'connecting' in status_word or 'connect' == status_word:
            self.set_armor_state('arming')
            self.hero_action.set_label('VERBINDUNG WIRD AUFGEBAUT')
        else:
            self._armor_pending = False
            self.set_armor_state('offline')
            self.hero_action.set_label('SCHNELL VERBINDEN')

        self.update_settings_ui()
        self.update_status_text(status_text, settings_text)
        if hasattr(self, 'sys_vpn_preview'):
            self.update_exact_system_preview()
        if hasattr(self, 'second_vpn_top'):
            state_txt = 'VPN: AKTIV' if connected else 'VPN: OFFLINE'
            top_txt = f'{state_txt}   |   Protokoll: {proto_text}   |   {uptime}'
            self.second_vpn_top.set_text(top_txt)
            self.second_dns_top.set_text(top_txt)
            self.second_status_top.set_text(top_txt)
        if hasattr(self, 'second_status_values'):
            vals = [
                'AKTIV' if connected else 'OFFLINE',
                self.display_country(country) if country else '-',
                pretty(city) if city else '-',
                ip,
                proto_text,
                uptime,
                '-',
            ]
            for w, v in zip(self.second_status_values, vals):
                w.set_text(v)
                ctx = w.get_style_context(); ctx.remove_class('second-value-good'); ctx.remove_class('second-value-bad')
            ctx = self.second_status_values[0].get_style_context(); ctx.add_class('second-value-good' if connected else 'second-value-bad')
            self.second_status_country.set_text((self.display_country(country) if country else 'VPN OFFLINE') + ('\n' + pretty(city) if city else ''))
        if self.mode == 'dns':
            self.update_dns_ui()
        return False

    def update_status_text(self, status_text, settings_text):
        self.detail.set_text((status_text or 'Kein Verbindungsstatus') + '\n\n' + (settings_text or 'Keine Einstellungen'))
        if hasattr(self, 'status_country'):
            connected = self.get_any(self.status_data, 'status').lower() == 'connected'
            country = self.get_any(self.status_data, 'country')
            city = self.get_any(self.status_data, 'city')
            country_name = self.display_country(country) if country else ''
            if connected:
                location = '\n'.join(x for x in (country_name.upper(), pretty(city)) if x)
                self.status_country.set_text(location or 'VPN VERBUNDEN')
                self.status_security.set_text('DEINE VERBINDUNG IST GESCHÜTZT')
                ctx = self.status_security.get_style_context()
                ctx.remove_class('statusbad')
                ctx.add_class('statusgood')
            else:
                self.status_country.set_text('VPN OFFLINE')
                self.status_security.set_text('DEINE VERBINDUNG IST NICHT GESCHÜTZT')
                ctx = self.status_security.get_style_context()
                ctx.remove_class('statusgood')
                ctx.add_class('statusbad')

    def hero_action_clicked(self):
        connected = self.get_any(self.status_data, 'status').lower() == 'connected'
        if connected:
            self.vpn_action(['nordvpn', 'disconnect'], record=None)
        else:
            self.vpn_action(['nordvpn', 'connect'], record='current')

    # ---------------- connections ----------------
    def connect_country(self):
        if self.selected_country:
            self.connect_target({'type': 'country', 'country': self.selected_country})

    def connect_target(self, target):
        typ = target.get('type')
        if typ == 'server':
            host = target.get('server', '').replace('.nordvpn.com', '')
            self.vpn_action(['nordvpn', 'connect', host], record=target)
        elif typ == 'city':
            self.vpn_action(
                ['nordvpn', 'connect', target['country'], target['city']],
                record=target,
            )
        else:
            self.vpn_action(['nordvpn', 'connect', target['country']], record=target)

    def connect_selected_server(self):
        if self.selected_server:
            self.connect_target(self.selected_server)

    def vpn_action(self, args, record=None):
        if self.busy:
            return
        self.busy = True
        is_connect = len(args) > 1 and args[1] == 'connect'
        if is_connect:
            self._armor_pending = True
            self.set_armor_state('arming')
        self.top_status.set_text('Bitte warten ...')
        def worker():
            rc, out = run_cmd(args)
            rec = record
            if rc == 0 and record == 'current':
                time.sleep(0.6)
                _, st = run_cmd(['nordvpn', 'status'])
                sd = kv(st)
                if sd.get('status', '').lower() == 'connected':
                    rec = {
                        'type': 'server',
                        'country': tokenise(sd.get('country', '')),
                        'city': tokenise(sd.get('city', '')),
                        'server': sd.get('hostname', '') or sd.get('server', ''),
                    }
            GLib.idle_add(self.finish_action, rc, out, rec)
        threading.Thread(target=worker, daemon=True).start()

    def finish_action(self, rc, out, record):
        self.busy = False
        if rc == 0 and isinstance(record, dict):
            self.add_recent(record)
        elif rc != 0 and out:
            self._armor_pending = False
            self.detail.set_text(out)
            self.set_armor_state('offline')
        self.refresh_all(force=True)
        return False

    # ---------------- settings logic ----------------
    def update_settings_ui(self):
        t = self.settings_data
        tech = self.get_any(t, 'technology').upper()
        proto = self.get_any(t, 'protocol').upper()
        if 'NORDWHISPER' in tech:
            active = 'nordwhisper'
        elif 'NORDLYNX' in tech:
            active = 'nordlynx'
        elif 'OPENVPN' in tech:
            active = 'openvpn_tcp' if 'TCP' in proto else 'openvpn_udp'
        else:
            active = None
        names = {
            'nordlynx': 'NORDLYNX',
            'nordwhisper': 'NORDWHISPER',
            'openvpn_tcp': 'OPENVPN TCP',
            'openvpn_udp': 'OPENVPN UDP',
        }
        for mode, b in self.proto_buttons.items():
            ctx = b.get_style_context()
            ctx.remove_class('activechoice')
            b.set_label(names[mode])
            if mode == active:
                ctx.add_class('activechoice')
                b.set_label('> ' + names[mode])
        self.set_toggle(self.btn_kill, 'KILL SWITCH', is_on(self.get_any(t, 'kill switch')))
        self.set_toggle(self.btn_auto, 'AUTO-CONNECT', is_on(self.get_any(t, 'auto-connect')))
        self.set_toggle(self.btn_pq, 'POST-QUANTUM', is_on(self.get_any(t, 'post-quantum vpn')))
        dns = self.get_any(t, 'dns')
        self.btn_dns.set_label('DNS   NORDVPN STANDARD' if self.dns_is_default(dns) else 'DNS   BENUTZERDEFINIERT')
        self.settings_note.set_text('NordVPN 5.3 Backend · Shield-TV Oberfläche')
        if hasattr(self, 'second_vpn_protocol'):
            self.second_vpn_protocol.set_text(names.get(active, 'UNBEKANNT'))
            self.second_vpn_auto.set_text('Ein' if is_on(self.get_any(t, 'auto-connect')) else 'Aus')
            self.second_vpn_kill.set_text('Ein' if is_on(self.get_any(t, 'kill switch')) else 'Aus')
            threat = is_on(self.get_any(t, 'threat protection lite'))
            self.second_vpn_threat.set_text('Ein' if threat else 'Aus')
            self.second_vpn_obf.set_text('Aus')
            connected = self.get_any(self.status_data, 'status').lower() == 'connected'
            self.second_vpn_quick.set_text('Verbunden' if connected else 'Bereit')
        if hasattr(self, 'settings_info'):
            active_name = names.get(active, 'UNBEKANNT')
            info = {
                'nordlynx': 'NordLynx ist das schnelle WireGuard-basierte NordVPN-Protokoll.\n\nEmpfohlen für die meisten Verbindungen.',
                'nordwhisper': 'NordWhisper ist für Netzwerke gedacht, in denen normale VPN-Protokolle eingeschränkt werden.',
                'openvpn_tcp': 'OpenVPN TCP priorisiert Zuverlässigkeit und kann in restriktiven Netzen stabiler sein.',
                'openvpn_udp': 'OpenVPN UDP bietet in der Regel die beste Kombination aus Geschwindigkeit und Sicherheit.',
            }.get(active, 'Wähle links ein VPN-Protokoll.')
            self.settings_info.set_text(f'AKTIV: {active_name}\n\n{info}')

    def set_toggle(self, b, name, on):
        ctx = b.get_style_context()
        ctx.remove_class('activechoice')
        b.set_label(f'{name}   {"EIN" if on else "AUS"}')
        if on:
            ctx.add_class('activechoice')

    def set_protocol(self, mode):
        commands = {
            'nordlynx': [['nordvpn', 'set', 'technology', 'nordlynx']],
            'nordwhisper': [
                ['nordvpn', 'set', 'pq', 'off'],
                ['nordvpn', 'set', 'technology', 'nordwhisper'],
            ],
            'openvpn_tcp': [
                ['nordvpn', 'set', 'pq', 'off'],
                ['nordvpn', 'set', 'technology', 'openvpn'],
                ['nordvpn', 'set', 'protocol', 'tcp'],
            ],
            'openvpn_udp': [
                ['nordvpn', 'set', 'pq', 'off'],
                ['nordvpn', 'set', 'technology', 'openvpn'],
                ['nordvpn', 'set', 'protocol', 'udp'],
            ],
        }[mode]
        self.run_setting_sequence(commands, reconnect=True)

    def toggle_setting(self, name):
        key = 'kill switch' if name == 'killswitch' else 'auto-connect'
        new = 'off' if is_on(self.get_any(self.settings_data, key)) else 'on'
        self.run_setting_sequence([['nordvpn', 'set', name, new]], reconnect=False)

    def toggle_pq(self):
        current = is_on(self.get_any(self.settings_data, 'post-quantum vpn'))
        commands = [['nordvpn', 'set', 'pq', 'off']] if current else [
            ['nordvpn', 'set', 'technology', 'nordlynx'],
            ['nordvpn', 'set', 'pq', 'on'],
        ]
        self.run_setting_sequence(commands, reconnect=True)

    def run_setting_sequence(self, commands, reconnect=False):
        if self.busy:
            return
        self.busy = True
        self.top_status.set_text('Einstellung wird geändert ...')
        def worker():
            _, st = run_cmd(['nordvpn', 'status'])
            sd = kv(st)
            connected = sd.get('status', '').lower() == 'connected'
            reconnect_target = None
            if connected:
                reconnect_target = {
                    'type': 'city' if sd.get('city') else 'country',
                    'country': tokenise(sd.get('country', '')),
                    'city': tokenise(sd.get('city', '')),
                }
            logs = []
            ok = True
            if reconnect and connected:
                rc, out = run_cmd(['nordvpn', 'disconnect'])
                logs.append(out)
                ok = rc == 0
            if ok:
                for cmd in commands:
                    rc, out = run_cmd(cmd)
                    logs.append(out)
                    if rc != 0:
                        ok = False
                        break
            if reconnect and connected and ok and reconnect_target:
                cmd = ['nordvpn', 'connect', reconnect_target['country']]
                if reconnect_target.get('city'):
                    cmd.append(reconnect_target['city'])
                rc, out = run_cmd(cmd)
                logs.append(out)
                ok = rc == 0
            GLib.idle_add(self.finish_setting_sequence, ok, '\n'.join(x for x in logs if x))
        threading.Thread(target=worker, daemon=True).start()

    def finish_setting_sequence(self, ok, log):
        self.busy = False
        if not ok and log:
            self.detail.set_text(log)
        self.refresh_all(force=True)
        return False

    def request_quit(self):
        if getattr(self, 'quit_in_progress', False):
            return
        self.quit_in_progress = True
        if hasattr(self, 'footer'):
            self.footer.set_text('QUIT: VPN wird sicher getrennt ...')

        def worker():
            rc, status = run_cmd(['nordvpn', 'status'])
            connected = 'status: connected' in (status or '').lower()
            ok = True
            message = ''
            if connected:
                rc, out = run_cmd(['nordvpn', 'disconnect'], timeout=40)
                ok = (rc == 0)
                message = out or ''
                if ok:
                    # Verify that the tunnel is actually down before allowing exit.
                    _, verify = run_cmd(['nordvpn', 'status'])
                    ok = 'status: connected' not in (verify or '').lower()
            GLib.idle_add(self.finish_quit, ok, message)

        threading.Thread(target=worker, daemon=True).start()

    def finish_quit(self, ok, message=''):
        self.quit_in_progress = False
        if ok:
            self.close()
        else:
            if hasattr(self, 'footer'):
                self.footer.set_text('QUIT BLOCKIERT: VPN konnte nicht getrennt werden')
            if hasattr(self, 'country_subtitle') and self.mode == 'country':
                self.country_subtitle.set_text('QUIT BLOCKIERT // VPN-TRENNUNG FEHLGESCHLAGEN')
        return False

    # ---------------- DNS ----------------
    def dns_value(self):
        return self.get_any(self.settings_data, 'dns')

    def dns_is_default(self, value=None):
        v = (self.dns_value() if value is None else value).strip().lower()
        return v in ('', 'off', 'disabled', 'false', '0', 'none', '-')

    def dns_addresses(self):
        value = self.dns_value()
        if self.dns_is_default(value):
            return []
        out = []
        for x in re.split(r'[,;\s]+', value):
            x = x.strip()
            if not x:
                continue
            try:
                ipaddress.IPv4Address(x)
            except Exception:
                continue
            if x not in out:
                out.append(x)
        return out[:3]

    def open_dns(self):
        self.mode = 'dns'
        self._set_country_page_geometry(False)
        if hasattr(self, 'top_bar'): self.top_bar.hide()
        if hasattr(self, 'footer_box'): self.footer_box.hide()
        self.stack.set_visible_child_name('dns')
        self.update_rail_active(None)
        self.update_dns_ui()
        self.set_nav_rows([[b] for b in self.dns_nav_buttons] + [[self.second_dns_sy, self.second_dns_quit]])

    def update_dns_ui(self):
        value = self.dns_value()
        if self.dns_is_default(value):
            text = 'NordDNS'
            self.dns_state.set_text('Aktiv: NordVPN Standard-DNS automatisch bei VPN-Verbindung')
        else:
            addrs = self.dns_addresses()
            text = 'NordDNS Privat' if addrs == list(NORD_DNS) else (value or 'Eigener DNS')
            self.dns_state.set_text('Aktiv: ' + value)
        if hasattr(self, 'second_dns_mode'):
            self.second_dns_mode.set_text(text)
            threat = is_on(self.get_any(self.settings_data, 'threat protection lite'))
            val = 'Ein' if threat else 'Aus'
            self.second_dns_ad.set_text(val)
            self.second_dns_malware.set_text(val)
            self.second_dns_tracker.set_text(val)

    def set_dns_auto(self):
        self.run_setting_sequence([['nordvpn', 'set', 'dns', 'off']], reconnect=True)

    def set_dns_fixed(self):
        self.run_setting_sequence([['nordvpn', 'set', 'dns', *NORD_DNS]], reconnect=True)

    def open_dns_keypad(self):
        self.mode = 'dnskey'
        addrs = self.dns_addresses()
        self.dns_buffers = [(addrs[i] if i < len(addrs) else '') for i in range(3)]
        self.dns_index = 0
        self.flag_pending = set()
        os.makedirs(FLAG_CACHE_DIR, exist_ok=True)
        self.dns_key_note.set_text('')
        self.refresh_dns_display()
        self.stack.set_visible_child_name('dnskey')
        rows = [self.dns_key_buttons[i:i+4] for i in range(0, len(self.dns_key_buttons), 4)]
        rows.append([self.dns_next, self.dns_clear, self.dns_save, self.dns_cancel])
        self.set_nav_rows(rows)

    def refresh_dns_display(self):
        lines = []
        for i, value in enumerate(self.dns_buffers):
            mark = '▶' if i == self.dns_index else ' '
            lines.append(f'{mark} DNS {i+1}: {value or "_"}')
        self.dns_display.set_text('    '.join(lines))

    def dns_key(self, key):
        value = self.dns_buffers[self.dns_index]
        if key == '⌫':
            value = value[:-1]
        elif key == '.':
            if len(value) < 15 and not value.endswith('.'):
                value += '.'
        elif key.isdigit() and len(value) < 15:
            value += key
        self.dns_buffers[self.dns_index] = value
        self.refresh_dns_display()

    def dns_next_field(self):
        self.dns_index = (self.dns_index + 1) % 3
        self.refresh_dns_display()

    def dns_clear_field(self):
        self.dns_buffers[self.dns_index] = ''
        self.refresh_dns_display()

    def save_custom_dns(self):
        vals = [x.strip() for x in self.dns_buffers if x.strip()]
        if not vals:
            self.dns_key_note.set_text('Mindestens eine IPv4-Adresse eingeben.')
            return
        good = []
        for x in vals:
            try:
                ipaddress.IPv4Address(x)
            except Exception:
                self.dns_key_note.set_text('Ungültige IPv4-Adresse: ' + x)
                return
            if x not in good:
                good.append(x)
        self.run_setting_sequence([['nordvpn', 'set', 'dns', *good[:3]]], reconnect=True)
        self.open_dns()

    def show_mode(self, mode):
        self._set_country_page_geometry(False)
        # Favorites are a first-class rail destination but reuse the HOME screen.
        if mode == 'favorites':
            self.mode = 'home'
            self.stack.set_visible_child_name('home')
            self.home_category = 1
            self.set_home_category(1)
            self.set_home_nav(focus_hero=False)
            return

        self.mode = mode
        if mode in ('settings', 'status'):
            if hasattr(self, 'top_bar'): self.top_bar.hide()
            if hasattr(self, 'footer_box'): self.footer_box.hide()
        else:
            if hasattr(self, 'top_bar'): self.top_bar.show()
            if hasattr(self, 'footer_box'): self.footer_box.show()
        self.stack.set_visible_child_name(mode)

        if mode == 'home':
            if hasattr(self, 'footer'):
                self.footer.set_text('← → Länder    OK verbinden    OK halten Details')
            self.set_home_category(self.home_category)
            self.set_home_nav(focus_hero=True)
        elif mode == 'settings':
            self.set_nav_rows([[w] for w in self.settings_widgets] + [[self.second_vpn_sy, self.second_vpn_quit]])
        elif mode == 'status':
            self.set_nav_rows([[self.status_refresh], [self.second_status_sy, self.second_status_quit]])

    def set_home_nav(self, focus_hero=True):
        cards = [w for w in self.home_card_box.get_children() if isinstance(w, Gtk.Button)]
        rows = [[self.hero_action], list(self.category_buttons), cards]
        self.set_nav_rows(rows, focus_first=False)
        if focus_hero and self.nav_rows:
            self.nav_row = 0
            self.nav_col = 0
            GLib.idle_add(self.nav_rows[0][0].grab_focus)
        elif len(self.nav_rows) > 2 and self.nav_rows[2]:
            self.nav_row = 2
            local = self.home_item_index - self.home_view_start
            self.nav_col = max(0, min(local, len(self.nav_rows[2]) - 1))
            GLib.idle_add(self.nav_rows[2][self.nav_col].grab_focus)

    def set_nav_rows(self, rows, focus_first=True):
        self.nav_rows = [list(r) for r in rows if r]
        if (
            getattr(self, 'mode', '') not in ('systemmenu', 'country')
            and hasattr(self, 'system_button')
        ):
            extra = []
            flat = [w for row in self.nav_rows for w in row]
            if self.system_button not in flat: extra.append(self.system_button)
            if hasattr(self, 'quit_button') and self.quit_button not in flat: extra.append(self.quit_button)
            if extra: self.nav_rows.append(extra)
        self.nav_row = 0
        self.nav_col = 0
        self.in_rail = False
        if focus_first and self.nav_rows and self.nav_rows[0]:
            GLib.idle_add(self.nav_rows[0][0].grab_focus)

    def update_rail_active(self, mode):
        # V9 has no side rail. Kept as a no-op for compatibility.
        return

    def rail_order(self):
        return ['home', 'favorites', 'settings', 'status']

    def active_rail_mode(self):
        if self.mode == 'home' and CATEGORY_GROUPS[self.home_category][1] == 'favorites':
            return 'favorites'
        if self.mode in ('settings', 'status'):
            return self.mode
        return 'home'

    def enter_rail(self):
        self.show_system_menu()

    def leave_rail(self):
        self.show_mode('home')

    def drawer_select(self, mode):
        if mode == 'favorites':
            self.show_mode('favorites')
        else:
            self.show_mode(mode)

    def move_rail(self, delta):
        order = self.rail_order()
        focus = self.get_focus()
        try:
            idx = [self.rail_buttons[m] for m in order].index(focus)
        except ValueError:
            idx = 0
        idx = (idx + delta) % len(order)
        self.rail_buttons[order[idx]].grab_focus()

    def activate_rail(self):
        focus = self.get_focus()
        for mode, button in self.rail_buttons.items():
            if button is focus:
                self.drawer_select(mode)
                return

    def locate_focus(self):
        focus = self.get_focus()
        for r, row in enumerate(self.nav_rows):
            for c, w in enumerate(row):
                if w is focus:
                    self.nav_row, self.nav_col = r, c
                    return r, c
        return self.nav_row, self.nav_col

    def focus_cell(self, r, c):
        if not self.nav_rows:
            return
        r = max(0, min(r, len(self.nav_rows)-1))
        row = self.nav_rows[r]
        if not row:
            return
        c = max(0, min(c, len(row)-1))
        self.nav_row, self.nav_col = r, c
        row[c].grab_focus()
        self.ensure_focus_visible(row[c])

    def move_content(self, dx, dy):
        if not self.nav_rows:
            return
        r, c = self.locate_focus()

        if dy:
            nr = r + dy
            if 0 <= nr < len(self.nav_rows):
                target_row = self.nav_rows[nr]
                if len(self.nav_rows[r]) > 1 and len(target_row) > 1:
                    frac = c / max(1, len(self.nav_rows[r]) - 1)
                    nc = round(frac * (len(target_row) - 1))
                else:
                    nc = min(c, len(target_row)-1)

                # When entering the country row, use the current global tile index.
                if self.mode == 'home' and nr == 2 and target_row:
                    nc = max(0, min(
                        self.home_item_index - self.home_view_start,
                        len(target_row)-1
                    ))
                elif self.mode == 'country' and nr == 1 and target_row:
                    idx, view = self._country_index_state(self.country_tab)
                    nc = max(0, min(idx - view, len(target_row)-1))
                self.focus_cell(nr, nc)
            return

        # HOME country/favorite/recent row behaves exactly like the launcher
        # application carousel: LEFT/RIGHT changes the global item index and
        # automatically slides the four visible tiles.
        if self.mode == 'home' and r == 2:
            if dx < 0:
                self.move_home_carousel(-1)
            elif dx > 0:
                self.move_home_carousel(1)
            return

        if self.mode == 'country' and r == 1:
            if dx < 0:
                self.move_country_carousel(-1)
            elif dx > 0:
                self.move_country_carousel(1)
            return

        if dx < 0:
            if c > 0:
                self.focus_cell(r, c-1)
        elif dx > 0:
            row = self.nav_rows[r]
            if c < len(row)-1:
                self.focus_cell(r, c+1)

    def ensure_focus_visible(self, widget):
        scroll = None
        if self.mode == 'home':
            scroll = self.home_scroll
        elif self.mode == 'country':
            scroll = self.country_scroll
        if not scroll:
            return
        try:
            child = scroll.get_child()
            coords = widget.translate_coordinates(child, 0, 0)
            if not coords:
                return
            x = coords[0]
            alloc = widget.get_allocation()
            left, right = x, x + alloc.width
            hadj = scroll.get_hadjustment()
            if left < hadj.get_value():
                hadj.set_value(left)
            elif right > hadj.get_value() + hadj.get_page_size():
                hadj.set_value(right - hadj.get_page_size())
        except Exception:
            pass

    def activate_focus(self):
        if self.in_rail:
            self.activate_rail()
            return
        w = self.get_focus()
        if isinstance(w, Gtk.Button):
            w.clicked()
        elif isinstance(w, Gtk.Entry):
            w.grab_focus()
            w.set_position(-1)

    def long_ok_fire(self):
        self.ok_timer = 0
        if not self.ok_down:
            return False
        target = self.widget_targets.get(self.get_focus())
        if not target:
            return False
        self.ok_long_fired = True
        typ = target.get('type')
        if typ == 'country':
            self.open_country(target.get('country'))
        elif typ == 'server':
            self.open_server(target)
        elif typ == 'city':
            self.open_server(target)
        return False

    def begin_ok_hold(self):
        if self.ok_down:
            return
        self.ok_down = True
        self.ok_long_fired = False
        if self.ok_timer:
            GLib.source_remove(self.ok_timer)
        self.ok_timer = GLib.timeout_add(700, self.long_ok_fire)

    def finish_ok_hold(self):
        if not self.ok_down:
            return
        self.ok_down = False
        if self.ok_timer:
            GLib.source_remove(self.ok_timer)
            self.ok_timer = 0
        if not self.ok_long_fired:
            self.activate_focus()
        self.ok_long_fired = False

    def on_key_release(self, _widget, event):
        if event.keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter, Gdk.KEY_space):
            self.finish_ok_hold()
            return True
        return False

    def on_key(self, _widget, event):
        key = event.keyval
        if key in (Gdk.KEY_Menu,):
            self.show_system_menu()
            return True

        if key in (Gdk.KEY_Up, Gdk.KEY_KP_Up):
            self.move_content(0, -1); return True
        if key in (Gdk.KEY_Down, Gdk.KEY_KP_Down):
            self.move_content(0, 1); return True
        if key in (Gdk.KEY_Left, Gdk.KEY_KP_Left):
            if self.mode in ('settings', 'dns'):
                w = self.get_focus()
                if isinstance(w, Gtk.Button):
                    w.clicked()
                    return True
            self.move_content(-1, 0); return True
        if key in (Gdk.KEY_Right, Gdk.KEY_KP_Right):
            if self.mode in ('settings', 'dns'):
                w = self.get_focus()
                if isinstance(w, Gtk.Button):
                    w.clicked()
                    return True
            self.move_content(1, 0); return True
        if key in (Gdk.KEY_Return, Gdk.KEY_KP_Enter, Gdk.KEY_space):
            self.begin_ok_hold(); return True
        if key in (Gdk.KEY_Escape, Gdk.KEY_BackSpace):
            if self.mode == 'server':
                self.return_to_country_detail()
            elif self.mode == 'country':
                self.show_mode('home')
            elif self.mode == 'dnskey':
                self.open_dns()
            elif self.mode == 'dns':
                self.show_system_menu()
            elif self.mode == 'systemmenu':
                self.show_mode('home')
            elif self.mode in ('settings', 'status'):
                self.show_system_menu()
            else:
                self.close()
            return True
        return False

if __name__ == '__main__':
    win = ShieldNordVPN()
    win.show_all()
    win.show_mode('home')
    Gtk.main()
