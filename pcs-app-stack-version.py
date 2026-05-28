#!/usr/bin/env python3

import argparse
import json
import logging
import os
import sys
import time
from typing import Optional, Any

import requests



##########################################################################################
# Process arguments / parameters.
##########################################################################################

pc_parser = argparse.ArgumentParser(description='What version is this app stack on?', prog=os.path.basename(__file__))


pc_parser.add_argument(
    '--ca_bundle',
    default=os.environ.get('CA_BUNDLE', None),
    type=str,
    help='(Optional) - Custom CA (bundle) file')
pc_parser.add_argument(
    '-s', '--stack',
    default='',
    type=str,
    help='(Optional) - Limit search to a stack (defined in the config file)')
pc_parser.add_argument(
    '-d', '--debug',
    action='store_true',
    help='(Optional) Enable debugging')

args = pc_parser.parse_args()

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if args.debug else logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)

##########################################################################################
# Helpers.
##########################################################################################

##########################################################################################
# Helpers.
##########################################################################################

def login(login_url: str, access_key: str, secret_key: str, ca_bundle: Optional[str]) -> str:
    url = f'{login_url}/login'
    headers = {'Content-Type': 'application/json'}
    requ_data = json.dumps({'username': access_key, 'password': secret_key})
    api_response = requests.post(url, headers=headers, data=requ_data, verify=ca_bundle)
    if api_response.ok:
        api_response = json.loads(api_response.content)
        token = api_response.get('token')
    else:
        logger.error(f'API ({url}) responded with an error\n{api_response.text}')
        sys.exit(1)
    logger.debug('POST')
    logger.debug(url)
    logger.debug(requ_data)
    logger.debug(api_response)
    return token

def execute(action: str, url: str, token: str, ca_bundle: Optional[str] = None, requ_data: Optional[str] = None) -> Optional[Any]:
    headers = {'Content-Type': 'application/json'}
    headers['x-redlock-auth'] = token
    method = getattr(requests, action.lower())
    api_response = method(url, headers=headers, data=requ_data, verify=ca_bundle)
    result = None
    if api_response.status_code in [401, 429, 500, 502, 503, 504]:
        for retry in range(1, 4):
            delay = 2 ** retry  # Exponential backoff: 2, 4, 8 seconds
            logger.debug(f'Retry {retry}/3 after {delay} seconds')
            time.sleep(delay)
            api_response = method(url, headers=headers, data=requ_data, verify=ca_bundle)
            if api_response.ok:
                break # retry loop
    logger.debug(action)
    logger.debug(url)
    logger.debug(requ_data)
    logger.debug(api_response.status_code)
    if api_response.ok:
        try:
            result = json.loads(api_response.content)
        except ValueError:
            logger.error(f'API ({url}) responded with an error\n{api_response.content}')
            sys.exit(1)
    return result


##########################################################################################
## Main.
##########################################################################################

CONFIG = {}
try:
    from config import *
except ImportError:
    logger.info('Error reading configuration file: verify config.py exists in the same directory as this script.')
    sys.exit(1)

configured = False
for stack in CONFIG['STACKS']:
    if CONFIG['STACKS'][stack]['access_key'] != None:
        configured = True
        break
if (not configured):
    logger.info('Error reading configuration file: verify credentials for at least one stack.')
    sys.exit(1)

if args.stack:
    configured = False
    for stack in CONFIG['STACKS']:
        if args.stack.lower() == stack.lower():
            if CONFIG['STACKS'][stack]['access_key'] != None:
                 configured = True
                 break
    if (not configured):
        logger.info('Error reading configuration file: verify credentials for the specified stack.')
        sys.exit(1)

if args.ca_bundle:
    CONFIG['CA_BUNDLE'] = args.ca_bundle




for stack in CONFIG['STACKS']:
    if args.stack and args.stack.lower() != stack.lower():
        continue
    if CONFIG['STACKS'][stack]['access_key']:
        token = login(CONFIG['STACKS'][stack]['url'], CONFIG['STACKS'][stack]['access_key'], CONFIG['STACKS'][stack]['secret_key'], CONFIG['CA_BUNDLE'])

        version = execute('GET', f"{CONFIG['STACKS'][stack]['url']}/version", token, CONFIG['CA_BUNDLE'])
        if version:
            logger.info(f"{CONFIG['STACKS'][stack]['url']} {version}")
        else:
            logger.info(f"{CONFIG['STACKS'][stack]['url']} - Error retrieving version")
               
