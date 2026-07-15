from getpass import getpass
from hashlib import sha256
from hmac import compare_digest


def main() -> None:
    token = getpass("Personal access key (at least 32 characters): ")
    if len(token) < 32:
        raise SystemExit("Personal access key must contain at least 32 characters")
    confirmation = getpass("Repeat personal access key: ")
    if not compare_digest(token, confirmation):
        raise SystemExit("Personal access keys do not match")
    print(sha256(token.encode("utf-8")).hexdigest())


if __name__ == "__main__":
    main()
