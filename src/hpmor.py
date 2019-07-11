#!/usr/bin/env python3

from pathlib import Path

import toml


def relpath(path):
    return Path(__file__).parent / path


def process(config, input_path, out_path):
    with open(input_path) as f:
        data = f.read()
    # TODO: actually process the files
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
        output_path = relpath(config["paths"]["target"]) / input_path.name
        if not output_path.parent.exists():
            output_path.parent.mkdir(parents=True)
        process(config, input_path, output_path)


if __name__ == "__main__":
    main()
