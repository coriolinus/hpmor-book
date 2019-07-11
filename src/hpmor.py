#!/usr/bin/env python3

import re
import unicodedata
from pathlib import Path

import toml
from bs4 import BeautifulSoup

BLOCK_SIZE = 10


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
    r = config["redo"]
    del config["interactive"]
    del config["redo"]

    with open(relpath("config.toml"), "w") as f:
        toml.dump(config, f)

    config["interactive"] = i
    config["redo"] = r


def extract_authornote_prefix_and_footnote(config, soup, title):
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

    def show_elements(block):
        block_start = BLOCK_SIZE * block
        block_end = block_start + BLOCK_SIZE
        for block_idx, element in enumerate(elements[block_start:block_end]):
            idx = block_start + block_idx
            el_str = (
                f"<{element.name}>" if element.name is not None else element.strip()
            )
            if len(el_str) == 0:
                continue

            print(f"{idx:04}: {el_str}")
        print()

    if config["interactive"] and (config["redo"] or n is None):
        # print descendants in batches of 10, with line numbers, until we're done
        d = n
        print()
        print(f"Interactive author-note selection for {title}:")
        for block in range(len(elements) // BLOCK_SIZE + 1):
            show_elements(block)

            print("Enter number of first non-author-note line, or")
            print(" n for the next block, or")
            print(" o to declare the whole chaper omake, or")
            if d is not None:
                print(f" d to use the current setting ({d})")
            print(" q to exit interactive selection for this file:")
            n = input("> ").strip().lower()
            print()

            if n == "" or n[0] == "n":
                continue

            if n[0] == "o":
                raise Omake()

            if n[0] == "d":
                if d is None:
                    print("no default known!")
                    continue

                n = d
                break

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

    try:
        footnote = config["footnotes"][title]
    except KeyError:
        footnote = None

    if config["interactive"] and (config["redo"] or footnote is None):
        # print tail of file in batches of block size, with line numbers, until we're done
        d = footnote
        print(f"Interactive footnote selection for {title}")
        for block in reversed(range(len(elements) // BLOCK_SIZE + 1)):
            show_elements(block)

            print("Enter number of last story line, or")
            print(" p for the prev block, or")
            if d is not None:
                print(f" d for existing default ({d})")
            print(" q to exit interactive selection for this file:")
            footnote = input("> ").strip().lower()
            print()

            if footnote == "" or footnote[0] == "p":
                continue

            if footnote[0] == "d":
                if d is None:
                    print("no default known!")
                    continue

                footnote = d
                break

            if footnote[0] == "q":
                footnote = -1
                break

            try:
                footnote = int(footnote)
            except ValueError:
                print("invalid input; aborting")
                footnote = None
                break

            if footnote == 0:
                footnote = -1

            break

    if footnote is not None:
        config.setdefault("footnotes", {})
        config["footnotes"][title] = footnote

        # just delete the footnote
        last_story_element = elements[footnote]
        while last_story_element.parent is not content:
            if last_story_element.parent is None:
                raise Exception("footnote iterated too far; did not stop at content")
            last_story_element = last_story_element.parent
        while (
            len(content.contents) > 0 and content.contents[-1] is not last_story_element
        ):
            content.contents.pop()

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
    chnum, _ = title.split(":", maxsplit=1)
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
            raise Exception("story iterated too far; did not stop at content")
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
        appendix = extract_authornote_prefix_and_footnote(config, soup, title)
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

    config["interactive"] = args.interactive
    config["redo"] = args.redo

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
