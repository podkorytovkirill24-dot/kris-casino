# Kris Casino Bot

Атмосферный Telegram-бот казино с пополнением через Crypto Pay (если задан токен) или через Send и админ-меню внутри бота.

## Быстрый старт

1. Установите зависимости:

```bash
python -m pip install -r requirements.txt
```

2. Создайте файл `.env` рядом с `main.py`:

```bash
BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN
ADMIN_IDS=123456789,987654321
SUPPORT_CONTACT=@your_support
SEND_USERNAME=@send
SEND_PAY_URL_TEMPLATE=
CRYPTO_PAY_API_TOKEN=
CRYPTO_PAY_BASE_URL=https://pay.crypt.bot/api
CRYPTO_PAY_ASSET=USDT
CRYPTO_PAY_DESCRIPTION=Kris Casino top-up
CRYPTO_PAY_ALLOW_COMMENTS=false
CRYPTO_PAY_ALLOW_ANONYMOUS=false
DB_PATH=data/kris_casino.db
MIN_DEPOSIT=5
MIN_BET=0.20
MAX_BET=200
CURRENCY=USDT
WIN_RATE=0.30
```

3. Запустите бота:

```bash
python main.py
```

## Bothost.ru

Если хостинг ожидает стартовый скрипт, используйте `start.sh` (Linux). В остальных случаях команда запуска — `python main.py`.

## Пополнения через Crypto Pay

Если задан `CRYPTO_PAY_API_TOKEN`, бот создает счета через Crypto Pay и автоматически проверяет оплату по кнопке «Я оплатил».

## Пополнения через Send

Если `SEND_PAY_URL_TEMPLATE` не задан, бот создаёт заявку и просит пользователя оплатить вручную через Send с комментарием. Админ подтверждает заявку в меню `Админка -> Пополнения`.

Можно подключить авто-оплату, если у вас есть готовый API Send. В этом случае задайте `SEND_PAY_URL_TEMPLATE` с плейсхолдерами `{amount}`, `{comment}`, `{invoice_id}` или расширьте `app/services/send_provider.py`.
