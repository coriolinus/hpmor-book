# HPMOR Book

[_Harry Potter and the Methods of Rationality_](http://www.hpmor.com/) is a very good book. Unfortunately, its presentation leaves something to be desired: its styling and presentation feels very much like it came straight from fanfiction.net, which isn't ideal when what you want is a nice ebook.

This project attempts to build a better ebook, with authors' notes, omake, and other distractions from the actual text moved into appendices.

## Usage

1. Fetch the HPMOR source data. A useful command:

    ```sh
    wget -nc -nH -w1 --random-wait -P book-src --cut-dirs=2 -r -l0 -k -m -Dwww.hpmor.com -Ichapter --adjust-extension http://www.hpmor.com/chapter/1
    ```

2. Run the converter:

    ```sh
    src/hpmor.py
    ```

3. If the output is not as desired, it's possible to adjust `config.toml` manually, but a better bet is often to use interactive mode.

    ```sh
    src/hpmor.py -i
    ```

    If the configuration is fully specified, but wrong, it's possible to interactively redo it:

    ```sh
    src/hpmor.py -iR
    ```
