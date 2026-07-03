"""Authentification Telegram interactive (à lancer UNE fois).

Usage :
    .venv/bin/python -m bot.telegram_login

Crée/sauvegarde la session (data/telegram_session) pour que TelegramAgent
puisse lire les canaux sans re-demander le code à chaque run.
"""
from __future__ import annotations

from bot.config import (TELEGRAM_API_HASH, TELEGRAM_API_ID,
                        TELEGRAM_PHONE, TELEGRAM_SESSION)


def main() -> None:
    try:
        from telethon import TelegramClient
    except Exception:
        print("telethon n'est pas installé.")
        return
    if not (TELEGRAM_API_ID and TELEGRAM_API_HASH):
        print("Configure TELEGRAM_API_ID et TELEGRAM_API_HASH dans .env "
              "(https://my.telegram.org → API development tools).")
        return
    client = TelegramClient(str(TELEGRAM_SESSION), int(TELEGRAM_API_ID), TELEGRAM_API_HASH)
    client.start(phone=TELEGRAM_PHONE or None)
    print(f"✅ Authentifié. Session sauvegardée : {TELEGRAM_SESSION}")
    client.disconnect()


if __name__ == "__main__":
    main()
