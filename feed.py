import logging


def get_specific_feed(feeds: dict, feed_name: str) -> str:
    for feed in feeds:
        if feed["name"] == feed_name:
            return feed["url"]
    raise ValueError(f"No '{feed_name}' feed found")


def get_system_information_feed(feeds: dict):
    return get_specific_feed(feeds, "system_information")


def get_station_information_feed(feeds: dict):
    return get_specific_feed(feeds, "station_information")


def get_station_status_feed(feeds: dict):
    return get_specific_feed(feeds, "station_status")


def get_language_text(texts: list[dict] | str, language: str | None = None) -> str:
    if type(texts) is str:  # No alternatives for languages
        return texts

    if language is None:
        logging.debug("No language specified, returning first found.")
        return texts[0]["text"]
    for name in texts:
        if name["language"] == language:
            return name["text"]
    raise ValueError(f"No text found for language '{language}'")
