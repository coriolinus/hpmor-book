#!/usr/bin/env python3

import re
import unicodedata
from pathlib import Path

import toml
from bs4 import BeautifulSoup


def slugify(value):
    """
    Normalizes string, converts to lowercase, removes non-alpha characters,
    and converts spaces to hyphens.

    https://stackoverflow.com/a/295466/504550
    """
    value = unicodedata.normalize("NFKD", value)
    value = re.sub(r"[^\w\s-]", "", value).strip().lower()
    value = re.sub(r"[-\s]+", "_", value)
    return value


def relpath(path):
    return Path(__file__).parent / path


def process(config, input_path, out_dir):
    with open(input_path) as f:
        data = f.read()

    soup = BeautifulSoup(data, "html5lib")
    for strip_selector in config["strip"]["selectors"]:
        for element in soup.select(strip_selector):
            element.decompose()

    title = soup.select(config["metadata"]["chapter_title"])[0].get_text()
    out_fn = Path(f"{int(input_path.stem):03}_{slugify(title)}{input_path.suffix}")
    print(out_fn)
    out_path = out_dir / out_fn

    data = soup.prettify()

    with open(out_path, "w") as f:
        f.write(data)


def main():
    with open(relpath("config.toml")) as f:
        config = toml.load(f)

    src = relpath(config["paths"]["source"])
    for output_path in relpath(config["paths"]["target"]).glob(
        f"*.{config['paths']['extension']}"
    ):
        output_path.unlink()

    for input_path in src.glob(f"*.{config['paths']['extension']}"):
        output_dir = relpath(config["paths"]["target"])
        if not output_dir.exists():
            output_dir.mkdir(parents=True)
        process(config, input_path, output_dir)


if __name__ == "__main__":
    main()
