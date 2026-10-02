"""Command-line account recovery for whoever runs the server.

Run from the repository root:

    python3 -m backend.manage users                      # list accounts
    python3 -m backend.manage set-email admin you@example.com
    python3 -m backend.manage reset-link admin           # print a 30-minute reset link
    python3 -m backend.manage test-email you@example.com # check SMTP settings
"""

import argparse

from dotenv import load_dotenv

load_dotenv()

from . import auth, mailer  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(prog="python3 -m backend.manage", description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("users", help="list accounts")
    p_email = sub.add_parser("set-email", help="link an email to an account (empty string to remove)")
    p_email.add_argument("username")
    p_email.add_argument("email")
    p_link = sub.add_parser("reset-link", help="print a password reset link for an account")
    p_link.add_argument("username")
    p_test = sub.add_parser("test-email", help="send a test email using the SMTP settings in .env")
    p_test.add_argument("to")
    args = parser.parse_args()

    if args.command == "users":
        for u in auth.list_users():
            print(f"{u['username']:<20} {u['role']:<6} {u['email'] or '-'}")
    elif args.command == "set-email":
        if args.username not in auth.load_users():
            parser.error(f"no such user: {args.username}")
        email = auth.set_email(args.username, args.email)
        print(f"{args.username}: email set to {email}" if email else f"{args.username}: email removed")
    elif args.command == "reset-link":
        if args.username not in auth.load_users():
            parser.error(f"no such user: {args.username}")
        link = f"{mailer.app_url()}/reset?token={auth.make_reset_token(args.username)}"
        print(f"Reset link for {args.username} (valid {auth.RESET_MAX_AGE // 60} minutes, single use):\n{link}")
    elif args.command == "test-email":
        try:
            mailer.send_test(args.to)
        except Exception as e:
            raise SystemExit(f"Sending failed: {e}")
        print(f"Test email sent to {args.to}")


if __name__ == "__main__":
    main()
