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
        "fields": ",".join(fields),
        "since": since,
        "limit": limit,
        "access_token": access_token,
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
        "Reposts",
        "Quotes",
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
            .strftime("%Y-%m-%d %H:%M")
        )

        if permalink in existing_map:
            row = existing_map[permalink]
            metrics = [
                post.get(m, 0)
                for m in ["views", "likes", "replies", "reposts", "quotes", "shares"]
            ]
            sheet.update(
                range_name=f"E{row}:J{row}",
                values=[metrics],
                value_input_option="USER_ENTERED",
            )
            logging.info(f"Updated row {row} for {permalink}")
        else:
            new_rows.append(
                [
                    idx,
                    ts_str,
                    post.get("text", ""),
                    "",
                    *[
                        post.get(m, 0)
                        for m in [
                            "views",
                            "likes",
                            "replies",
                            "reposts",
                            "quotes",
                            "shares",
                        ]
                    ],
                    permalink,
                ]
            )
            idx += 1

    for row in new_rows:
        sheet.append_row(values=row, value_input_option="USER_ENTERED")
    logging.info(f"Appended {len(new_rows)} new rows.")

    apply_formatting(
        sheet, service, spreadsheet_id, worksheet_name, start_idx
    )


def apply_formatting(sheet, service, spreadsheet_id, worksheet_name, start_idx):
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
        # 1) Left-align only column D (Topic)
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
                    "startColumnIndex": 10,
                    "endColumnIndex": 11,
                    "startRowIndex": 1                },
                "cell": {
                    "userEnteredFormat": {
                        "horizontalAlignment": "LEFT"
                    }
                },
                "fields": "userEnteredFormat.horizontalAlignment"
            }
        },
        # 3) Lock row height
        {
            "updateDimensionProperties": {
                "range": {
                    "sheetId": sheet_id,
                    "dimension": "ROWS",
                    "startIndex": 1,
                    "endIndex": last_idx,
                },
                "properties": {
                    "pixelSize": 100
                },
                "fields": "pixelSize"
            }
        },
        # 4) Bold header row
        {
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 0,
                    "endRowIndex": 1
                },
                "cell": {
                    "userEnteredFormat": {
                        "textFormat": {
                            "bold": True
                        }
                    }
                },
                "fields": "userEnteredFormat.textFormat.bold"
            }
        },
        # 5) Topic dropdown (column D)
        {
            "setDataValidation": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": start_idx,
                    "endRowIndex": last_idx,
                    "startColumnIndex": 3,
                    "endColumnIndex": 4,
                },
                "rule": {
                    "condition": {
                        "type": "ONE_OF_LIST",
                        "values": [{"userEnteredValue": v} for v in ["AI", "Storytelling"]],
                    },
                    "showCustomUi": True,
                    "strict": True,
                },
            }
        },
        # 6) Conditional formatting for views > 10000
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
                            "backgroundColor": {"red": 1.0000, "green": 0.7765, "blue": 0.7922}
                        }
                    }
                },
                "index": 0
            }
        },
        # 7) Conditional formatting for 5000 ≤ views ≤ 10000
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
                            "backgroundColor": {"red": 1.0000, "green": 0.8980, "blue": 0.9059}
                        }
                    }
                },
                "index": 1
            }
        }    
    ]

    dropdown_colors = {
        "AI": {"red": 1.0000, "green": 1.0000, "blue": 0.8745},
        "Storytelling": {"red": 0.7843, "green": 0.9294, "blue": 0.9686},
    }

    color_rules = [
        {
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [
                        {
                            "sheetId": sheet_id,
                            "startRowIndex": 1,
                            "endRowIndex": last_idx,
                            "startColumnIndex": 3,
                            "endColumnIndex": 4,
                        }
                    ],
                    "booleanRule": {
                        "condition": {
                            "type": "TEXT_EQ",
                            "values": [{"userEnteredValue": label}],
                        },
                        "format": {"backgroundColor": color},
                    },
                },
                "index": idx,
            }
        }
        for idx, (label, color) in enumerate(dropdown_colors.items())
    ]

    requests.extend(color_rules)
 
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
