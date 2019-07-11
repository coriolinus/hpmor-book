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


class Omake(Exception):
    """
    Omake are intentionally non-canonical chapters which should be moved into an 
    appendix.
    """

    pass


def dumpconfig(config):
    i = config["interactive"]
    del config["interactive"]
    with open(relpath("config.toml"), "w") as f:
        toml.dump(config, f)
    config["interactive"] = i


def extract_authornote_prefix(config, soup, title):
    try:
        if title in config["omake"]:
            raise Omake()
    except KeyError:
        pass

    try:
        n = config["author_notes"][title]
    except KeyError:
        n = None

    content = soup.select(config["metadata"]["story_container"])[0]
    elements = list(content.descendants)

    if n is None and config["interactive"]:
        block_size = 10
        # print descendants in batches of 10, with line numbers, until we're done
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

            print()
            print("Enter number of first non-author-note line, or")
            print(" n for the next block, or")
            print(" o to declare the whole chaper omake, or")
            print(" q to exit interactive selection for this file:")
            n = input("> ").strip().lower()
            print()

            if n == "" or n[0] == "n":
                continue

            if n[0] == "o":
                raise Omake()

            if n[0] == "q":
                return None

            try:
                n = int(n)
            except ValueError:
                print("invalid input; aborting")
                return None

            break

    if n is None:
        return None

    config.setdefault("author_notes", {})
    config["author_notes"][title] = n
    dumpconfig(config)

    if n == 0:
        return None

    # since we know we have some appendix notes at this point, let's make the
    # framework into which we'll stuff this appendix
    #
    # copy the object
    appendix = BeautifulSoup(str(soup), "html5lib")
    # clear out the body
    acontent = appendix.select(config["metadata"]["story_container"])[0]
    acontent.contents = []

    # update the title
    chnum, _ = title.split(":")
    appendix_title = f"Appendix A: {chnum} Author's Notes"
    atitle = appendix.select(config["metadata"]["chapter_title"])[0]
    atitle.string = appendix_title
    appendix.html.head.title.string = (
        f"Harry Potter and the Methods of Rationality, {appendix_title}"
    )

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

    title = (
        soup.select(config["metadata"]["chapter_title"])[0]
        .get_text()
        .replace("\n", " ")
    )
    out_fn = Path(f"{int(input_path.stem):03}_{slugify(title)}{input_path.suffix}")
    print(out_fn)

    try:
        appendix = extract_authornote_prefix(config, soup, title)
    except Omake:
        out_fn = Path(f"appendix_b_{out_fn}")
        config.setdefault("omake", [])
        config["omake"].append(title)
        dumpconfig(config)

    else:
        if appendix is not None:
            a_fn = Path(f"appendix_a_{out_fn}")
            a_path = out_dir / a_fn
            with open(a_path, "w") as f:
                f.write(str(appendix))

    out_path = out_dir / out_fn
    with open(out_path, "w") as f:
        f.write(str(soup))


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-i",
        "--interactive",
        action="store_true",
        help="use interactive mode to separate headers and footers",
    )
    parser.add_argument(
        "-R",
        "--redo",
        action="store_true",
        help="redo interactive mode for chapters already configured",
    )
    args = parser.parse_args()

    with open(relpath("config.toml")) as f:
        config = toml.load(f)

    if args.redo and "author_notes" in config:
        del config["author_notes"]

    config["interactive"] = args.interactive

    src = relpath(config["paths"]["source"])
    for output_path in relpath(config["paths"]["target"]).glob(
        f"*.{config['paths']['extension']}"
    ):
        output_path.unlink()

    try:
        for input_path in src.glob(f"*.{config['paths']['extension']}"):
            output_dir = relpath(config["paths"]["target"])
            if not output_dir.exists():
                output_dir.mkdir(parents=True)
            process(config, input_path, output_dir)
    except KeyboardInterrupt:
        # we don't need a traceback in this case
        pass


if __name__ == "__main__":
    main()
