# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Chicago Transit Board - A Flask web application that displays real-time train arrivals for CTA (Chicago Transit Authority) and Metra Electric Line from stations near downtown Chicago.

## Commands

```bash
# Run the web application
python app.py

# Run CLI versions (standalone scripts)
python cta.py        # CTA arrivals only
python metra.py      # Metra arrivals only
python dashboard.py  # Combined dashboard
```

## Required Environment Variables

Create a `.env` file with:
- `CTA_API_KEY` - Get from https://www.transitchicago.com/developers/
- `METRA_API_TOKEN` - Get from https://metra.com/developers

## Architecture

**app.py** - Main Flask application
- `/` route serves the dashboard
- `get_cta_arrivals()` - Fetches from CTA Train Tracker REST API, returns arrivals grouped by line (next 3 per line)
- `get_metra_arrivals()` - Fetches from Metra GTFS Realtime API (Protocol Buffers), returns next 5 trains

**Standalone scripts** (`cta.py`, `metra.py`, `dashboard.py`) - CLI versions that print to terminal, useful for testing API responses

**templates/index.html** - Jinja2 template with auto-refresh every 30 seconds, styled with CTA line colors

## API Details

- **CTA**: REST API returning JSON, queries multiple station IDs (Clark/Lake, Washington/Wabash, Lake)
- **Metra**: GTFS Realtime Protocol Buffers, filters for Metra Electric (ME) route at Millennium Station

## Dependencies

Flask, requests, python-dotenv, gtfs-realtime-bindings (provides `google.transit.gtfs_realtime_pb2`)
