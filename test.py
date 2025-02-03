#!/usr/bin/env python3
"""
run.py - Command-line script to fetch Archive URLs from the Wayback Machine
         in real-time (line-by-line streaming) and print them in the console.

Usage:
  1) python run.py example.com
     (Replace 'example.com' with the domain you want to fetch)

  2) You can also run without arguments:
     python run.py
     Then you’ll be prompted for a domain.

Dependencies:
  pip install requests
"""

import sys
import requests

def fetch_archive_urls(domain):
    """
    Fetches Archive URLs for the given domain, streaming line by line from the
    Wayback Machine's CDX endpoint, and prints them in real time.
    """
    base_url = "https://web.archive.org/cdx/search/cdx"
    params = {
        "url": f"{domain}*",
        "output": "text",
        "fl": "original",
        "collapse": "urlkey"
    }

    print(f"Fetching archive URLs for domain: {domain}\n")
    line_count = 0

    try:
        # Use stream=True so we can process lines as they arrive
        with requests.get(base_url, params=params, stream=True) as r:
            r.raise_for_status()
            # read line by line
            for line in r.iter_lines(decode_unicode=True):
                if line:
                    url_str = line.strip()
                    line_count += 1
                    print(url_str)
    except requests.exceptions.RequestException as err:
        print(f"Error: {err}")
        return

    print(f"\nDone. Total URLs fetched: {line_count}\n")


def main():
    # If domain given in argv, use that. Otherwise prompt user.
    if len(sys.argv) > 1:
        domain = sys.argv[1].strip()
    else:
        domain = input("Enter domain (e.g. example.com): ").strip()

    if not domain:
        print("Error: please enter a valid domain.")
        sys.exit(1)

    fetch_archive_urls(domain)


if __name__ == "__main__":
    main()
