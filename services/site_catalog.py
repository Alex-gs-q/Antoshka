from __future__ import annotations

from typing import Dict, Optional

from core.text_norm import normalize_text


SITE_ALIASES: Dict[str, str] = {
    "vk": "https://vk.com",
    "vkontakte": "https://vk.com",
    "yandex": "https://ya.ru",
    "ya": "https://ya.ru",
    "yandeks": "https://ya.ru",
    "yandex muzyka": "https://music.yandex.ru",
    "yandeks muzyka": "https://music.yandex.ru",
    "yandex maps": "https://yandex.ru/maps",
    "yandeks karty": "https://yandex.ru/maps",
    "yandex translate": "https://translate.yandex.ru",
    "yandeks perevodchik": "https://translate.yandex.ru",
    "yandex news": "https://news.yandex.ru",
    "yandeks novosti": "https://news.yandex.ru",
    "yandex mail": "https://mail.yandex.ru",
    "yandeks pochta": "https://mail.yandex.ru",
    "google": "https://www.google.com",
    "gmail": "https://mail.google.com",
    "google maps": "https://maps.google.com",
    "google translate": "https://translate.google.com",
    "youtube": "https://youtube.com",
    "tiktok": "https://tiktok.com",
    "instagram": "https://instagram.com",
    "twitch": "https://twitch.tv",
    "reddit": "https://reddit.com",
    "x": "https://x.com",
    "twitter": "https://x.com",
    "telegram": "https://web.telegram.org",
    "discord": "https://discord.com/app",
    "whatsapp": "https://web.whatsapp.com",
    "github": "https://github.com",
    "steam": "https://store.steampowered.com",
    "spotify": "https://open.spotify.com",
    "netflix": "https://netflix.com",
    "wikipedia": "https://wikipedia.org",
    "chatgpt": "https://chatgpt.com",
}


def resolve_site(text: str, custom: Optional[Dict[str, str]] = None) -> Optional[str]:
    if not text:
        return None
    t = normalize_text(text)
    for prefix in ("na ", "v ", "vo "):
        if t.startswith(prefix):
            t = t[len(prefix):]
    custom = custom or {}
    custom_norm = {normalize_text(k): v for k, v in custom.items()}
    if t in custom_norm:
        return custom_norm[t]
    if t in SITE_ALIASES:
        return SITE_ALIASES[t]
    return None
