#!/usr/bin/env python3

""" Where? """

import argparse
import json
import logging
import os
import re
import signal
import sys
import tempfile
import time

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

import requests

from dateutil.tz import gettz

# pylint: disable=import-error
import arrow

##########################################################################################
# Process arguments / parameters.
##########################################################################################

pc_parser = argparse.ArgumentParser(description='Where is this Tenant? Who are its users and when did they last login?', prog=os.path.basename(__file__))

pc_parser.add_argument(
    'customer_name',
    type=str,
    help='*Required* Customer Name, or filename containing a (JSON) array of Customer Names')
pc_parser.add_argument(
    '--ca_bundle',
    default='',
    #default=os.environ.get('CA_BUNDLE', None),
    type=str,
    help='(Optional) - Custom CA (bundle) file')
pc_parser.add_argument(    '-s', '--stack',
    default='',
    type=str,
    help='(Optional) - Limit search to a stack (defined in the config file)')
pc_parser.add_argument(
    '-c', '--cache',
    action='store_true',
    help='(Optional) Cache responses from the API (eight hour lifetime)')
pc_parser.add_argument(
    '-d', '--debug',
    action='store_true',
    help='(Optional) Enable debugging')
pc_parser.add_argument(
    '-u', '--users',
    action='store_true',
    help='(Optional) Enumerate tenant users and their last login time')
pc_parser.add_argument(
    '--sort',
    default='name',
    choices=['login', 'name'],
    help="(Optional) Sort tenant users by login or name (Default: 'name')")
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

def handler(_signum, _frame):
    print()
    sys.exit(1)

signal.signal(signal.SIGINT, handler)

def login(login_url: str, access_key: str, secret_key: str, ca_bundle: str) -> Optional[str]:
    url = f'{login_url}/login'
    headers = {'Content-Type': 'application/json'}
    requ_data = json.dumps({'username': access_key, 'password': secret_key})
    api_response = requests.post(url, headers=headers, data=requ_data, verify=ca_bundle)
    auth_token = None
    if api_response.ok:
        api_response = json.loads(api_response.content)
        auth_token = api_response.get('token')
    else:
        logger.error(f'API ({url}) responded with an error\n{api_response.text}')
    logger.debug('POST')
    logger.debug(url)
    logger.debug(requ_data)
    logger.debug(api_response)
    return auth_token

def execute(action: str, url: str, auth_token: str, ca_bundle: Optional[str] = None, requ_data: Optional[str] = None) -> Optional[Any]:
    headers = {'Content-Type': 'application/json'}
    headers['x-redlock-auth'] = auth_token
    method = getattr(requests, action.lower())
    api_response = method(url, headers=headers, data=requ_data, verify=ca_bundle)
    result = None
    if api_response.status_code in [401, 429, 500, 502, 503, 504]:
        logger.info(f'Exceptional API response code {api_response.status_code} received from {url}. Waiting and then retrying')
        for retry in range(1, 4):
            delay = 2 ** retry  # Exponential backoff: 2, 4, 8 seconds
            logger.debug(f'Retry {retry}/3 after {delay} seconds')
            time.sleep(delay)
            api_response = method(url, headers=headers, data=requ_data, verify=ca_bundle)
            if api_response.ok:
                break # retry loop
    if api_response.status_code == 403:
        logger.error('403 Unauthorized: check that credentials are valid and are authorized to access the API.')
        return result
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

def define_usage(url: str, auth_token: str, ca_bundle: str, tenant: Dict[str, Any], range: str) -> None:
    usage_query = json.dumps({'customerName': tenant['customerName'], 'timeRange': {'type':'relative','value': {'amount': 1,'unit': range}}})
    usage = execute('POST', f'{url}/_support/license/api/v1/usage/time_series', auth_token, ca_bundle, usage_query)
    logger.debug(json.dumps(usage, indent=4))
    if usage and 'dataPoints' in usage and len(usage['dataPoints']) > 0:
        current_usage = usage['dataPoints'][-1]
        if 'counts' in current_usage and len(current_usage['counts']) > 0:
            current_usage_count = sum(sum(c.values()) for c in current_usage['counts'].values())
            logger.info(f'\tCredit snapshot, end of period ({range}):  {current_usage_count}')

def find_customer(stack_name: str, tenant_list: Optional[List[Dict[str, Any]]], customer_name: str, url: str, ca_bundle: str, auth_token: str) -> int:
    count = 0
    if not tenant_list:
        return count
    customer_name_lower = customer_name.lower()
    for tenant in tenant_list:
        customer_lower = tenant['customerName'].lower()
        prisma_id = str(tenant['prismaId'])
        tenant_id = ''
        serial_num = ''
        if tenant['licenseDetails']['marketplaceData'] is not None:
            tenant_id = str(tenant['licenseDetails']['marketplaceData']['tenantId'])
            serial_num = str(tenant['licenseDetails']['marketplaceData']['serialNumber'])
        if customer_name_lower in customer_lower or customer_name_lower in prisma_id or customer_name_lower in tenant_id or customer_name_lower in serial_num:
            logger.info(f"{customer_name} found on {stack_name} as {tenant['customerName']}")
            logger.debug(json.dumps(tenant, indent=4))
            logger.info(f"\tCustomer ID:   {tenant['customerId']}")
            if 'marketplaceData' in tenant['licenseDetails'] and tenant['licenseDetails']['marketplaceData']:
                if 'serialNumber' in tenant['licenseDetails']['marketplaceData']:
                    logger.info(f"\tSerial Number: {tenant['licenseDetails']['marketplaceData']['serialNumber']}")
                if 'tenantId' in tenant['licenseDetails']['marketplaceData']:
                    logger.info(f"\tTenant ID:     {tenant['licenseDetails']['marketplaceData']['tenantId']}")
                if 'endTs' in tenant['licenseDetails'] and tenant['licenseDetails']['endTs']:
                    end_dt = datetime.fromtimestamp(tenant['licenseDetails']['endTs']/1000.0)
                    logger.info(f'\tRenewal Date:  {end_dt}')
            logger.info(f"\tPrisma ID:     {tenant['prismaId']}")
            logger.info(f"\tEval:          {tenant['eval']}")
            logger.info(f"\tActive:        {tenant['active']}")
            logger.info(f"\tCredits Available:       {tenant['workloads']}")
            define_usage(url, auth_token, ca_bundle, tenant, "day")
            define_usage(url, auth_token, ca_bundle, tenant, "month")
            define_usage(url, auth_token, ca_bundle, tenant, "year")

            print()
            if args.users:
                users_query = json.dumps({'customerName': tenant['customerName']})
                users = execute('POST', f'{url}/v2/_support/user', auth_token, ca_bundle, users_query)
                logger.debug(json.dumps(users, indent=4))
                if users:
                    logger.info(f"{'Name':<25}\t\t{'Email Address':<33}\t\tLast Login")
                    logger.info(f"{'----':<25}\t\t{'-------------':<33}\t\t----------")
                    if args.sort == 'login':
                        users = sorted(users, key=lambda u: u['lastLoginTs'], reverse=True)
                    for user in users:
                        last_login = ''
                        time_zone = gettz(user['timeZone'])
                        if user['lastLoginTs'] == -1:
                            last_login = 'Never'
                        else:
                            arrow_time = arrow.Arrow.fromtimestamp(user['lastLoginTs']/1000, time_zone)
                            last_login = f"{arrow_time.format('YYYY-MM-DD')} - {arrow_time.humanize()}"
                        logger.info(f"{user['displayName']:<25}\t\t{user['email']:<33}\t\t{last_login}")
            count += 1
    print()
    return count

##########################################################################################
## Main.
##########################################################################################

CONFIG = {}
try:
    # pylint: disable=wildcard-import
    from config import *
except ImportError:
    logger.info('Error reading configuration file: verify config.py exists in the same directory as this script.')
    sys.exit(1)

configured = False
for stack in CONFIG['STACKS']:
    if CONFIG['STACKS'][stack]['access_key'] is not None:
        configured = True
        break
if not configured:
    logger.info('Error reading configuration file: verify credentials for at least one stack.')
    sys.exit(1)

if args.stack:
    configured = False
    for stack in CONFIG['STACKS']:
        if args.stack.lower() == stack.lower():
            if CONFIG['STACKS'][stack]['access_key'] is not None:
                configured = True
                break
    if not configured:
        logger.info('Error reading configuration file: verify credentials for the specified stack.')
        sys.exit(1)

if args.ca_bundle:
    CONFIG['CA_BUNDLE'] = args.ca_bundle

if os.path.isfile(args.customer_name):
    with open(args.customer_name, 'r', encoding='utf8') as f:
        CONFIG['CUSTOMERS'] = json.load(f)
else:
    CONFIG['CUSTOMERS'] = [args.customer_name]

for customer in CONFIG['CUSTOMERS']:
    found = 0
    for stack in CONFIG['STACKS']:
        if args.stack and args.stack.lower() != stack.lower():
            continue
        if CONFIG['STACKS'][stack]['access_key']:
            logger.info(f'Checking: {stack}')
            print()
            token = login(CONFIG['STACKS'][stack]['url'], CONFIG['STACKS'][stack]['access_key'], CONFIG['STACKS'][stack]['secret_key'], CONFIG['CA_BUNDLE'])
            if not token:
                logger.info(f'Skipping {stack} because of authentication failure.')
                print()
                continue
            customers_file_name = os.path.join(tempfile.gettempdir(), f"{re.sub(r'\W+', '', stack).lower()}-customers.json")
            if os.path.isfile(customers_file_name):
                hours_ago = datetime.now() - timedelta(hours=8)
                customers_file_date = datetime.fromtimestamp(os.path.getctime(customers_file_name))
                if customers_file_date < hours_ago or args.cache is False:
                    logger.debug(f'Deleting cached stack file: {customers_file_name}')
                    os.remove(customers_file_name)
            if os.path.isfile(customers_file_name):
                with open(customers_file_name, 'r', encoding='utf8') as f:
                    logger.debug(f'Reading cached stack file: {customers_file_name}')
                    tenants = json.load(f)
            else:
                tenants = execute('GET', f"{CONFIG['STACKS'][stack]['url']}/_support/customer", token, CONFIG['CA_BUNDLE'])
                if tenants and args.cache:
                    with open(customers_file_name, 'w', encoding='utf8') as result_file:
                        json.dump(tenants, result_file)
            found += find_customer(stack, tenants, customer, CONFIG['STACKS'][stack]['url'], CONFIG['CA_BUNDLE'], token)
    if found == 0:
        logger.info(f'{customer} not found on any configured stack')
    print()
