#!/usr/bin/env python3
"""
Gmail Email Cleanup Script with Command-Line Options
Deletes emails older than N months while preserving custom-labeled emails.

Usage:
    python3 gmail_cleanup.py --months 3 --dry-run
    python3 gmail_cleanup.py --protect-keywords invoice,receipt
    python3 gmail_cleanup.py --exclude-from newsletter@example.com
"""

import os
import pickle
import sys
import logging
import argparse
from datetime import datetime, timedelta
from typing import List, Set

try:
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
    import googleapiclient.discovery
except ImportError:
    print("Error: Google API libraries not installed")
    print("Run: pip3 install google-auth-oauthlib google-auth-httplib2 googleapiclient")
    sys.exit(1)

# Parse command-line arguments
parser = argparse.ArgumentParser(
    description='Gmail Email Cleanup Tool',
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog="""
Examples:
  python3 gmail_cleanup.py --months 6
  python3 gmail_cleanup.py --dry-run
  python3 gmail_cleanup.py --protect-keywords invoice,receipt,contract
  python3 gmail_cleanup.py --exclude-from newsletter@example.com,promo@store.com
  python3 gmail_cleanup.py --protect-labels Important,Family,Work
  python3 gmail_cleanup.py --cleanup-labels Promotions,Archives
  python3 gmail_cleanup.py --notify your-email@gmail.com
  python3 gmail_cleanup.py --debug
    """
)
parser.add_argument('--months', type=int, default=3, help='Delete emails older than X months (default: 3)')
parser.add_argument('--dry-run', action='store_true', help='Preview without deleting')
parser.add_argument('--exclude-from', type=str, help='Exclude emails from senders (comma-separated)')
parser.add_argument('--protect-labels', type=str, help='Protect emails with these labels (comma-separated)')
parser.add_argument('--protect-keywords', type=str, help='Protect emails with keywords in subject (comma-separated)')
parser.add_argument('--cleanup-labels', type=str, help='Only clean emails in these labels (comma-separated)')
parser.add_argument('--notify', type=str, help='Send summary email to this address')
parser.add_argument('--debug', action='store_true', help='Enable debug logging')

args = parser.parse_args()

# Configuration
MONTHS_OLD = args.months
DRY_RUN = args.dry_run
EXCLUDE_FROM = [e.strip() for e in args.exclude_from.split(',')] if args.exclude_from else []
PROTECT_LABELS = [l.strip() for l in args.protect_labels.split(',')] if args.protect_labels else []
PROTECT_KEYWORDS = [k.strip() for k in args.protect_keywords.split(',')] if args.protect_keywords else ['receipt']
CLEANUP_LABELS = [l.strip() for l in args.cleanup_labels.split(',')] if args.cleanup_labels else []
NOTIFY_EMAIL = args.notify
DEBUG = args.debug

SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

# Setup logging
def setup_logging():
    log_level = logging.DEBUG if DEBUG else logging.INFO
    log_filename = 'gmail_cleanup.log'
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logging.info("="*80)
    logging.info("Gmail Cleanup Script Started")
    logging.info(f"Configuration: MONTHS_OLD={MONTHS_OLD}, DRY_RUN={DRY_RUN}")
    if EXCLUDE_FROM:
        logging.info(f"Excluding from: {', '.join(EXCLUDE_FROM)}")
    if PROTECT_LABELS:
        logging.info(f"Protecting labels: {', '.join(PROTECT_LABELS)}")
    if PROTECT_KEYWORDS:
        logging.info(f"Protecting keywords: {', '.join(PROTECT_KEYWORDS)}")
    if CLEANUP_LABELS:
        logging.info(f"Cleanup labels only: {', '.join(CLEANUP_LABELS)}")
    logging.info("="*80)


class GmailCleanup:
    def __init__(self):
        self.service = None
        self.authenticate()
        
    def authenticate(self):
        logging.info("Authenticating with Gmail API...")
        creds = None
        
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists('credentials.json'):
                    logging.error("credentials.json not found!")
                    sys.exit(1)
                
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)
        
        self.service = googleapiclient.discovery.build('gmail', 'v1', credentials=creds)
        logging.info("Successfully authenticated")
    
    def get_all_labels(self):
        logging.info("Fetching labels...")
        try:
            results = self.service.users().labels().list(userId='me').execute()
            labels = results.get('labels', [])
            
            system_labels = {
                'INBOX', 'SENT', 'DRAFT', 'TRASH', 'SPAM', 'IMPORTANT',
                'STARRED', 'UNREAD', 'CATEGORY_PERSONAL', 'CATEGORY_SOCIAL',
                'CATEGORY_PROMOTIONS', 'CATEGORY_UPDATES', 'CATEGORY_FORUMS'
            }
            
            custom_labels = {
                label['id']: label['name']
                for label in labels
                if label['id'] not in system_labels
            }
            
            logging.info(f"Found {len(custom_labels)} custom labels")
            return custom_labels
        except Exception as error:
            logging.error(f"Error fetching labels: {error}")
            return {}
    
    def build_search_query(self):
        """Build Gmail search query based on configuration"""
        cutoff_date = (datetime.now() - timedelta(days=MONTHS_OLD*30)).strftime('%Y-%m-%d')
        query = f'before:{cutoff_date} -is:starred -is:important'
        
        # Exclude specific senders
        for sender in EXCLUDE_FROM:
            query += f' -from:{sender}'
        
        # Protect keywords in subject
        for keyword in PROTECT_KEYWORDS:
            query += f' -subject:{keyword}'
        
        # Only cleanup specific labels
        if CLEANUP_LABELS:
            label_query = ' OR '.join([f'label:{label}' for label in CLEANUP_LABELS])
            query += f' ({label_query})'
        
        return query
    
    def search_emails(self):
        query = self.build_search_query()
        logging.info(f"Searching for emails older than {MONTHS_OLD} months...")
        logging.debug(f"Search query: {query}")
        
        try:
            message_ids = []
            request = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=500
            )
            
            while request:
                results = request.execute()
                messages = results.get('messages', [])
                message_ids.extend([msg['id'] for msg in messages])
                
                if 'nextPageToken' in results:
                    request = self.service.users().messages().list(
                        userId='me',
                        q=query,
                        pageToken=results['nextPageToken'],
                        maxResults=500
                    )
                else:
                    request = None
                
                logging.info(f"Found {len(message_ids)} emails so far...")
            
            logging.info(f"Total: {len(message_ids)} emails")
            return message_ids
        except Exception as error:
            logging.error(f"Error searching: {error}")
            return []
    
    def get_email_info(self, message_id):
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='metadata',
                metadataHeaders=['Subject', 'From', 'Date']
            ).execute()
            
            headers = {h['name']: h['value'] for h in message['payload'].get('headers', [])}
            
            return {
                'id': message_id,
                'subject': headers.get('Subject', '(no subject)'),
                'from': headers.get('From', '(unknown)'),
                'labels': set(message.get('labelIds', []))
            }
        except Exception as error:
            logging.error(f"Error getting email info: {error}")
            return None
    
    def filter_emails(self, message_ids, custom_labels):
        logging.info(f"Checking {len(message_ids)} emails for custom labels...")
        custom_label_ids = set(custom_labels.keys())
        
        to_delete = []
        to_keep = []
        
        for i, msg_id in enumerate(message_ids):
            if (i + 1) % 100 == 0:
                logging.info(f"Processed {i + 1}/{len(message_ids)}...")
            
            email_info = self.get_email_info(msg_id)
            if not email_info:
                continue
            
            # Check if email has any custom labels
            has_custom_label = bool(email_info['labels'] & custom_label_ids)
            
            # Check for protected labels
            has_protected_label = False
            if PROTECT_LABELS:
                email_custom_label_names = [
                    custom_labels.get(lid, '')
                    for lid in email_info['labels']
                    if lid in custom_labels
                ]
                for protect_label in PROTECT_LABELS:
                    if any(protect_label.lower() in label.lower() for label in email_custom_label_names):
                        has_protected_label = True
                        break
            
            if has_custom_label or has_protected_label:
                to_keep.append(email_info)
            else:
                to_delete.append(msg_id)
        
        logging.info(f"To delete: {len(to_delete)}")
        logging.info(f"To keep: {len(to_keep)}")
        
        return to_delete, to_keep
    
    def delete_emails(self, message_ids):
        if not message_ids:
            logging.info("No emails to delete")
            return 0
        
        logging.info(f"Deleting {len(message_ids)} emails...")
        deleted_count = 0
        
        for i, msg_id in enumerate(message_ids):
            try:
                if (i + 1) % 50 == 0:
                    logging.info(f"Deleted {i + 1}/{len(message_ids)}...")
                
                self.service.users().messages().trash(userId='me', id=msg_id).execute()
                deleted_count += 1
            except Exception as error:
                logging.warning(f"Failed to delete {msg_id}: {error}")
        
        logging.info(f"Deleted {deleted_count}/{len(message_ids)}")
        return deleted_count
    
    def run(self):
        logging.info("\nStep 1: Identifying custom labels...")
        custom_labels = self.get_all_labels()
        
        logging.info("\nStep 2: Searching for old emails...")
        message_ids = self.search_emails()
        
        if not message_ids:
            logging.info("No emails to delete")
            return
        
        logging.info("\nStep 3: Filtering by custom labels...")
        to_delete, to_keep = self.filter_emails(message_ids, custom_labels)
        
        logging.info("\nStep 4: Deleting...")
        if to_delete:
            if DRY_RUN:
                logging.info(f"DRY RUN: Would delete {len(to_delete)} emails")
            else:
                self.delete_emails(to_delete)
        
        logging.info("\n" + "="*80)
        logging.info("Complete!")
        logging.info("="*80)


def main():
    try:
        setup_logging()
        cleanup = GmailCleanup()
        cleanup.run()
    except KeyboardInterrupt:
        logging.warning("Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logging.error(f"Error: {e}", exc_info=DEBUG)
        sys.exit(1)


if __name__ == '__main__':
    main()
