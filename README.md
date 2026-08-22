# Gumroad Intel

A small, standard-library Python toolkit for pulling Gumroad product and sales data and analyzing store performance locally.

## Privacy warning

Gumroad sales exports contain customer information. Raw API responses, reports, and generated analysis are intentionally excluded from Git. Never commit the `data/`, `out/`, or `REPORT.md` paths.

## Authentication

Set `GUMROAD_ACCESS_TOKEN` in the environment, or store it in:

```text
~/.config/gumroad/credentials.env
```

with this format:

```text
GUMROAD_ACCESS_TOKEN=replace-me
```

Never place a live token inside this repository.

## Pull data

```bash
python pull.py
```

To also retrieve offer-code metadata:

```bash
python pull.py --offer-codes
```

Private responses are written under `data/`.

## Analyze locally

```bash
python analyze.py
```

The analysis reads local JSON files and does not make API calls or write data.

## Offer-code cleanup

`purge_offer_codes.py` audits stale offer codes and runs as a dry run by default:

```bash
python purge_offer_codes.py
```

Review its output carefully. `--apply` performs destructive API mutations; use `--canary --apply` first when appropriate.

## Requirements

Python 3.10 or later. Runtime code uses only the Python standard library.
