from __future__ import annotations

import random
from typing import List

from core.logger import setup_logger


def pick_suggestions(registry, lang: str, context: str, k: int = 5) -> List[str]:
    log = setup_logger()
    lang = (lang or "ru").lower()
    ctx = (context or "default").lower()
    groups = registry.examples_by_group(lang)
    all_examples = registry.get_all_examples(lang)

    group_map = {
        "start": ["help", "general", "timers", "notes", "open_web", "system"],
        "timers": ["timers", "alarms", "reminders"],
        "alarms": ["alarms", "timers"],
        "reminders": ["reminders", "timers"],
        "notes": ["notes"],
        "open_web": ["open_web"],
        "open_apps": ["open_apps"],
        "system": ["system"],
        "chat": ["chat", "general"],
        "voice": ["voice", "tts"],
        "tts": ["tts"],
        "help": ["help", "general"],
        "settings": ["settings"],
        "unknown": ["help", "general", "system"],
        "unknown_fallback": ["help", "general", "system"],
        "default": ["general", "help", "timers", "notes", "open_web", "system", "settings"],
    }

    selected_groups = group_map.get(ctx, [ctx, "general"])
    pool: List[str] = []
    for g in selected_groups:
        pool.extend(groups.get(g, []))

    if len(pool) < k:
        pool.extend(all_examples)

    unique = list(dict.fromkeys([p for p in pool if isinstance(p, str) and p.strip()]))

    if len(unique) >= k:
        picked = random.sample(unique, k=k)
    else:
        picked = unique

    if len(picked) < k:
        fallback = unique[:]
        for item in fallback:
            if item not in picked:
                picked.append(item)
            if len(picked) >= k:
                break

    picked = picked[:k]
    log.info(
        "SUGGESTIONS_PICK lang=%s ctx=%s pool=%s picked=%s",
        lang,
        ctx,
        len(unique),
        len(picked),
    )
    return picked
