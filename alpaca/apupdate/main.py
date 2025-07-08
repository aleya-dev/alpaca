from argparse import ArgumentParser, Namespace
from alpaca.common.alpaca_application import handle_main
from alpaca.configuration import Configuration
from alpaca.repository_cache import RepositoryCache


def _create_arg_parser(parser: ArgumentParser) -> ArgumentParser:
    parser.add_argument("--reset", "-r", action="store_true", help="Reset the repository cache and for a redownload.")
    return parser


def _update_main(args: Namespace, config: Configuration):
    repository_cache = RepositoryCache(config)

    if not args.reset:
        repository_cache.update_cache()
    else:
        repository_cache.reset_cache()


def main():
    handle_main(
        "update",
        require_root=True,
        disallow_root=False,
        create_arguments_callback=_create_arg_parser,
        main_function_callback=_update_main)


if __name__ == "__main__":
    main()
