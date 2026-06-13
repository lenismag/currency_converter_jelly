import requests
import json
import time
import urllib3

# Отключаем предупреждения о небезопасном соединении (необязательно) (verify=False)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class APIException(Exception):
    """Собственное исключение для ошибок API или ввода пользователя"""
    pass


class CurrencyConverter:
    CACHE_FILE = 'rates_cache.json'   # файл для хранения курсов
    CACHE_LIFETIME = 86400            # 24 часа в секундах

    @staticmethod
    def _get_rates():
        """
        Возвращает курсы валют из кэша или загружает с ЦБ РФ (раз в сутки).
        Возвращает словарь: {'USD': float, 'EUR': float, 'RUB': 1.0}
        """
        # 1. Пытаемся прочитать кэш
        try:
            with open(CurrencyConverter.CACHE_FILE, 'r', encoding='utf-8') as f:
                cache = json.load(f)
                if time.time() - cache['timestamp'] < CurrencyConverter.CACHE_LIFETIME:
                    return cache['rates']
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            pass  # кэш отсутствует или повреждён — идём за новыми курсами

        # 2. Загружаем свежие курсы (с отключённой проверкой SSL)
        return CurrencyConverter._fetch_and_cache_rates()

    @staticmethod
    def _fetch_and_cache_rates():
        """Загружает курсы с cbr-xml-daily.ru и сохраняет в кэш (verify=False)"""
        print("Загружаю свежие курсы валют с ЦБ РФ...")
        url = 'https://www.cbr-xml-daily.ru/daily_json.js'
        try:
            # verify=False — обход ошибки SSL (для работы в сетях с подменой сертификатов, например, рабочий комп)
            response = requests.get(url, verify=False)
            data = response.json()

            rates = {
                'USD': data['Valute']['USD']['Value'],
                'EUR': data['Valute']['EUR']['Value'],
                'RUB': 1.0
            }

            # Сохраняем в файл
            with open(CurrencyConverter.CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump({
                    'timestamp': time.time(),
                    'rates': rates
                }, f, ensure_ascii=False, indent=2)

            print("Курсы успешно загружены и сохранены.")
            return rates

        except Exception as e:
            raise APIException(f'Не удалось загрузить курсы валют: {e}')

    @staticmethod
    def get_price(base: str, quote: str, amount: float) -> float:
        """
        base, quote – коды валют (USD, EUR, RUB)
        amount – количество (положительное число)
        Возвращает сумму в валюте quote.
        """
        if base == quote:
            raise APIException('Нельзя переводить валюту саму в себя')
        if amount <= 0:
            raise APIException('Количество должно быть больше нуля')

        rates = CurrencyConverter._get_rates()

        if base not in rates:
            raise APIException(f'Валюта {base} не поддерживается (доступны: USD, EUR, RUB)')
        if quote not in rates:
            raise APIException(f'Валюта {quote} не поддерживается (доступны: USD, EUR, RUB)')

        # Конвертация через рубль
        amount_in_rub = amount * rates[base]
        result = amount_in_rub / rates[quote]
        return round(result, 2)