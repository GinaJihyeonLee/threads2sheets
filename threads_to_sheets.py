#!/usr/bin/env python3
"""
threads_to_sheets.py

Fetches posts from Threads and updates a Google Spreadsheet with metrics.

Usage:
    python threads_to_sheets.py \
        --access-token YOUR_TOKEN \
        --creds-json /path/to/credentials.json \
        --spreadsheet-id YOUR_SHEET_ID \
        --worksheet SHEET_NAME \
        --since YYYY-MM-DD \
        [--until YYYY-MM-DD] \
        [--limit 100]

Built-in formatting:
  - Updates existing rows (permalink match) for metrics columns
  - Appends new posts as additional rows
  - Applies readability-enhancing styles, add dropdown menu for the "Topic", and 
    conditional formatting for the "Views"
"""
import argparse
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# Timezone for converting timestamps
KST = ZoneInfo("Asia/Seoul")

# Google API scopes
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]


def fetch_threads_posts(access_token, since, until=None, limit=100):
    """
    Fetches posts from Threads API within a date range.
    Filters out REPOST_FACADE entries.
    """
    fields = [
        "id",
        "media_type",
        "permalink",
        "text",
        "timestamp",
        "is_quote_post",
    ]
    params = {
        "access_token": access_token,
        "fields": ",".join(fields),
        "since": since,
        "limit": limit
    }
    if until:
        params["until"] = until

    url = "https://graph.threads.net/v1.0/me/threads"
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    posts = resp.json().get("data", [])
    return [p for p in posts if p.get("media_type") != "REPOST_FACADE"]


def refine_posts_stats(posts, access_token):
    """
    Enriches each post with insights metrics: views, likes, replies, reposts, quotes, shares.
    """
    metrics = [
        "views",
        "likes",
        "replies",
        "reposts",
        "quotes",
        "shares"
    ]

    for post in posts:
        media_id = post.get("id")
        if not media_id:
            continue

        url = f"https://graph.threads.net/v1.0/{media_id}/insights"
        resp = requests.get(
            url,
            params={
                "metric": ",".join(metrics),
                "access_token": access_token,
            },
        )
        resp.raise_for_status()
        for entry in resp.json().get("data", []):
            name = entry.get("name")
            values = entry.get("values", [])
            post[name] = values[0].get("value", 0) if values else 0

    return posts


def get_gspread_client(creds_json):
    creds = ServiceAccountCredentials.from_json_keyfile_name(
        creds_json, SCOPES
    )
    return gspread.authorize(creds)


def get_sheets_service(creds_json):
    creds = Credentials.from_service_account_file(
        creds_json, scopes=SCOPES
    )
    return build("sheets", "v4", credentials=creds)


def update_sheet(stats, sheet, service, spreadsheet_id, worksheet_name):
    """
    Updates or appends rows in the given worksheet, then applies formatting.
    """
    records = sheet.get_all_records()
    header = [
        "Idx",
        "Date",
        "Text",
        "Topic",
        "Views",
        "Likes",
        "Replies",
        "Reposts/Quotes",
        "Shares",
        "Permalink",
    ]

    if not records:
        sheet.append_row(values=header, value_input_option="USER_ENTERED")
        existing_map = {}
        start_idx = 1
    else:
        existing_map = {
            rec["Permalink"]: idx + 2
            for idx, rec in enumerate(records)
            if rec.get("Permalink")
        }
        start_idx = len(records) + 1

    new_rows = []
    idx = start_idx

    for post in sorted(stats, key=lambda x: x["timestamp"]):
        permalink = post.get("permalink", "")
        ts_str = (
            datetime.fromisoformat(
                post["timestamp"].replace("+0000", "+00:00")
            )
            .astimezone(KST)
            .strftime("%Y. %m. %d %H:%M")
        )

        if permalink in existing_map:
            row = existing_map[permalink]
            metrics = [
                post.get("views", 0),
                post.get("likes", 0),
                post.get("replies", 0),
                post.get("reposts", 0) + post.get("quotes", 0),
                post.get("shares", 0)
            ]
            sheet.update(
                range_name=f"E{row}:I{row}",
                values=[metrics],
                value_input_option="USER_ENTERED",
            )
            logging.info(f"Updated row {row} for {permalink}")
        else:
            new_rows.append(
                [
                    idx,
                    f"'{ts_str}",  # Add apostrophe to force text format
                    post.get("text", "").split('\n')[0] if post.get("text") else "",
                    "",
                    post.get("views", 0),
                    post.get("likes", 0),
                    post.get("replies", 0),
                    post.get("reposts", 0) + post.get("quotes", 0),
                    post.get("shares", 0),
                    permalink,
                ]
            )
            idx += 1

    for row in new_rows:
        sheet.append_row(values=row, value_input_option="USER_ENTERED")
    logging.info(f"Appended {len(new_rows)} new rows.")

    apply_formatting(
        sheet, service, spreadsheet_id, worksheet_name
    )


def apply_formatting(sheet, service, spreadsheet_id, worksheet_name):
    """
    Applies styling, dropdowns, and conditional formatting rules.
    """
    # Fetch spreadsheet metadata
    meta = (
        service.spreadsheets()
        .get(spreadsheetId=spreadsheet_id)
        .execute()
    )
    sheet_id = next(s['properties']['sheetId'] for s in meta['sheets'] if s['properties']['title'] == worksheet_name)

    last_idx = len(sheet.get_all_values())

    requests = [
        # 0) Alignment: center all cells
        {
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id
                },
                "cell": {
                    "userEnteredFormat": {
                        "horizontalAlignment": "CENTER",
                        "verticalAlignment": "MIDDLE"
                    }
                },
                "fields": "userEnteredFormat(horizontalAlignment,verticalAlignment)"
            }
        },
        # 1) Left-align only column C (Text)
        {
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startColumnIndex": 2,
                    "endColumnIndex": 3,
                    "startRowIndex": 1                },
                "cell": {
                    "userEnteredFormat": {
                        "horizontalAlignment": "LEFT"
                    }
                },
                "fields": "userEnteredFormat.horizontalAlignment"
            }
        },
        # 2) Left-align only column J (Permalink)
        {
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startColumnIndex": 9,
                    "endColumnIndex": 10,
                    "startRowIndex": 1                },
                "cell": {
                    "userEnteredFormat": {
                        "horizontalAlignment": "LEFT"
                    }
                },
                "fields": "userEnteredFormat.horizontalAlignment"
            }
        },
        # 3) Set column widths
        {
            "updateDimensionProperties": {
                "range": {
                    "sheetId": sheet_id,
                    "dimension": "COLUMNS",
                    "startIndex": 3,  # Column D (Topic)
                    "endIndex": 4
                },
                "properties": {
                    "pixelSize": 200
                },
                "fields": "pixelSize"
            }
        },
        {
            "updateDimensionProperties": {
                "range": {
                    "sheetId": sheet_id,
                    "dimension": "COLUMNS",
                    "startIndex": 4,  # Column E (Views)
                    "endIndex": 5
                },
                "properties": {
                    "pixelSize": 120
                },
                "fields": "pixelSize"
            }
        },
        {
            "updateDimensionProperties": {
                "range": {
                    "sheetId": sheet_id,
                    "dimension": "COLUMNS",
                    "startIndex": 5,  # Column F (Likes)
                    "endIndex": 6
                },
                "properties": {
                    "pixelSize": 120
                },
                "fields": "pixelSize"
            }
        },
        {
            "updateDimensionProperties": {
                "range": {
                    "sheetId": sheet_id,
                    "dimension": "COLUMNS",
                    "startIndex": 6,  # Column G (Replies)
                    "endIndex": 7
                },
                "properties": {
                    "pixelSize": 120
                },
                "fields": "pixelSize"
            }
        },
        {
            "updateDimensionProperties": {
                "range": {
                    "sheetId": sheet_id,
                    "dimension": "COLUMNS",
                    "startIndex": 7,  # Column H (Reposts/Quotes)
                    "endIndex": 8
                },
                "properties": {
                    "pixelSize": 120
                },
                "fields": "pixelSize"
            }
        },
        {
            "updateDimensionProperties": {
                "range": {
                    "sheetId": sheet_id,
                    "dimension": "COLUMNS",
                    "startIndex": 8,  # Column I (Shares)
                    "endIndex": 9
                },
                "properties": {
                    "pixelSize": 120
                },
                "fields": "pixelSize"
            }
        },
        # Set widths for columns A, B, C
        {
            "updateDimensionProperties": {
                "range": {
                    "sheetId": sheet_id,
                    "dimension": "COLUMNS",
                    "startIndex": 0,  # Column A (Idx)
                    "endIndex": 1
                },
                "properties": {
                    "pixelSize": 50
                },
                "fields": "pixelSize"
            }
        },
        {
            "updateDimensionProperties": {
                "range": {
                    "sheetId": sheet_id,
                    "dimension": "COLUMNS",
                    "startIndex": 1,  # Column B (Date)
                    "endIndex": 2
                },
                "properties": {
                    "pixelSize": 150
                },
                "fields": "pixelSize"
            }
        },
        {
            "updateDimensionProperties": {
                "range": {
                    "sheetId": sheet_id,
                    "dimension": "COLUMNS",
                    "startIndex": 2,  # Column C (Text)
                    "endIndex": 3
                },
                "properties": {
                    "pixelSize": 600
                },
                "fields": "pixelSize"
            }
        },
        {
            "autoResizeDimensions": {
                "dimensions": {
                    "sheetId": sheet_id,
                    "dimension": "COLUMNS",
                    "startIndex": 9,
                    "endIndex": 10
                }
            }
        },
        # 4) Style header row - light navy background, white text, bold, black borders
        {
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 0,
                    "endRowIndex": 1
                },
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": {
                            "red": 0.2,
                            "green": 0.3,
                            "blue": 0.6
                        },
                        "textFormat": {
                            "bold": True,
                            "foregroundColor": {
                                "red": 1.0,
                                "green": 1.0,
                                "blue": 1.0
                            }
                        },
                        "borders": {
                            "top": {
                                "style": "SOLID",
                                "color": {"red": 0, "green": 0, "blue": 0}
                            },
                            "bottom": {
                                "style": "SOLID",
                                "color": {"red": 0, "green": 0, "blue": 0}
                            },
                            "left": {
                                "style": "SOLID",
                                "color": {"red": 0, "green": 0, "blue": 0}
                            },
                            "right": {
                                "style": "SOLID",
                                "color": {"red": 0, "green": 0, "blue": 0}
                            }
                        }
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,textFormat,borders)"
            }
        },
        # 5) Conditional formatting for views > 10000 - light yellow background, red bold text
        {
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [{
                        "sheetId": sheet_id,
                        "startColumnIndex": 4,
                        "endColumnIndex": 5,
                        "startRowIndex": 1
                    }],
                    "booleanRule": {
                        "condition": {
                            "type": "NUMBER_GREATER",
                            "values": [{"userEnteredValue": "10000"}]
                        },
                        "format": {
                            "backgroundColor": {"red": 1.0, "green": 1.0, "blue": 0.8},
                            "textFormat": {
                                "bold": True,
                                "foregroundColor": {"red": 1.0, "green": 0.0, "blue": 0.0}
                            }
                        }
                    }
                },
                "index": 0
            }
        },
        # 6) Conditional formatting for 5000 ≤ views ≤ 10000 - light red background, red bold text
        {
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [{
                        "sheetId": sheet_id,
                        "startColumnIndex": 4,
                        "endColumnIndex": 5,
                        "startRowIndex": 1
                    }],
                    "booleanRule": {
                        "condition": {
                            "type": "NUMBER_BETWEEN",
                            "values": [{"userEnteredValue": "5000"}, {"userEnteredValue": "10000"}]
                        },
                        "format": {
                            "backgroundColor": {"red": 1.0, "green": 0.9, "blue": 0.9},
                            "textFormat": {
                                "bold": True,
                                "foregroundColor": {"red": 1.0, "green": 0.0, "blue": 0.0}
                            }
                        }
                    }
                },
                "index": 1
            }
        }    
    ]
 
    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id, body={"requests": requests}
    ).execute()

def main():
    parser = argparse.ArgumentParser(description="Sync Threads stats to Google Sheets.")
    parser.add_argument('--access-token', required=True, help='Threads API access token')
    parser.add_argument('--creds-json', required=True, help='Path to Google service account credentials')
    parser.add_argument('--spreadsheet-id', required=True, help='Google Spreadsheet ID')
    parser.add_argument('--worksheet', required=True, help='Worksheet/tab name')
    parser.add_argument('--since', required=True, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--until', help='End date (YYYY-MM-DD)')
    parser.add_argument('--limit', type=int, default=100, help='Max posts to fetch')
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Initialize clients
    client = get_gspread_client(args.creds_json)
    sheet = client.open_by_key(args.spreadsheet_id).worksheet(args.worksheet)
    service = get_sheets_service(args.creds_json)

    # Fetch, process, and update
    posts = fetch_threads_posts(args.access_token, args.since, args.until, args.limit)
    stats = refine_posts_stats(posts, args.access_token)
    update_sheet(stats, sheet, service, args.spreadsheet_id, args.worksheet)

if __name__ == '__main__':
    main()
