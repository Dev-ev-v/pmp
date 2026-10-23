import logging
import typer

from pmp.cli.app import app


def main():

    typer.run(app)


if __name__ == "__main__":
    main()