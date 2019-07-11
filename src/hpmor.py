#!/usr/bin/env python3

import re
import unicodedata
from pathlib import Path

import toml
from bs4 import BeautifulSoup


def slugify(value):
    """
    Normalizes string, converts to lowercase, removes non-alpha characters,
    and converts spaces to underscores.

    https://stackoverflow.com/a/295466/504550
    """
    value = unicodedata.normalize("NFKD", value)
    value = re.sub(r"[^\w\s-]", "", value).strip().lower()
    value = re.sub(r"[-\s]+", "_", value)
    return value


def relpath(path):
    return Path(__file__).parent / path


def extract_authornote_prefix(config, soup, title):
    content = soup.select(config["metadata"]["story_container"])[0]

    # print descendants in batches of 10, with line numbers, until we're done
    block_size = 10
    elements = list(content.descendants)
    print(f"Interactive author-note selection for {title}:")
    for block in range(len(elements) // block_size):
        block_start = block_size * block
        block_end = block_start + block_size
        for block_idx, element in enumerate(elements[block_start:block_end]):
            idx = block_start + block_idx
            el_str = (
                f"<{element.name}>" if element.name is not None else element.strip()
            )
            if len(el_str) == 0:
                continue

            print(f"{idx:04}: {el_str}")

        print("Enter number of first non-author-note line, or")
        print(" n for the next block, or")
        print(" q to exit interactive selection for this file:")
        n = input("> ").strip().lower()
        if n == "" or n[0] == "n":
            continue

        if n[0] == "q":
            return None

        try:
            n = int(n)
        except ValueError:
            print("invalid input; aborting")
            return None

        if n == 0:
            return None

        break

    # since we know we have some appendix notes at this point, let's make the
    # framework into which we'll stuff this appendix
    #
    # copy the object
    appendix = BeautifulSoup(str(soup), "html5lib")
    # clear out the body
    acontent = appendix.select(config["metadata"]["story_container"])[0]
    acontent.contents = []

    # update the title
    atitle = appendix.select(config["metadata"]["chapter_title"])[0]
    atitle.string = f"Appendix 1: {title}"

    first_story_element = elements[n]
    # move upwards until we have a direct child of content
    while first_story_element.parent is not content:
        if first_story_element.parent is None:
            raise Exception("iterated too far; did not stop at content")
        first_story_element = first_story_element.parent

    # now move authors notes into the appendix
    while len(content.contents) > 0 and content.contents[0] is not first_story_element:
        acontent.append(content.contents[0].extract())

    return appendix


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

    if config["interactive"]:
        appendix = extract_authornote_prefix(config, soup, title)
        if appendix is not None:
            a_fn = Path(f"appendix_1_{out_fn}")
            a_path = out_dir / a_fn
            with open(a_path, "w") as f:
                f.write(appendix.prettify())

    with open(out_path, "w") as f:
        f.write(soup.prettify())


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-i",
        "--interactive",
        action="store_true",
        help="use interactive mode to separate headers and footers",
    )
    args = parser.parse_args()

    with open(relpath("config.toml")) as f:
        config = toml.load(f)

    config["interactive"] = args.interactive

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
