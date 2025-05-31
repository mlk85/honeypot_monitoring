import csv
import time
import os
import gspread

from web3 import Web3
from dotenv import load_dotenv
from oauth2client.service_account import ServiceAccountCredentials


load_dotenv()

CONTRACT_ADDRESS = os.getenv('CONTACT_ADDRESS')
INFURA_URL = os.getenv('INFURA_URL')
SHEET_ID = os.getenv('SHEET_ID')

# ABI (skrót — tylko potrzebne eventy)
ABI = [
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "address", "name": "attacker", "type": "address"},
            {"indexed": False, "internalType": "uint256", "name": "value", "type": "uint256"},
            {"indexed": False, "internalType": "uint256", "name": "attemptNum", "type": "uint256"},
            {"indexed": False, "internalType": "bool", "name": "wasBlacklisted", "type": "bool"},
            {"indexed": False, "internalType": "uint256", "name": "timestamp", "type": "uint256"}
        ],
        "name": "AttemptDetailed",
        "type": "event"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "address", "name": "attacker", "type": "address"},
            {"indexed": False, "internalType": "uint256", "name": "timestamp", "type": "uint256"}
        ],
        "name": "Caught",
        "type": "event"
    }
]

#Web3
web3 = Web3(Web3.HTTPProvider(INFURA_URL))
contract = web3.eth.contract(address=CONTRACT_ADDRESS, abi=ABI)

#Google sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)
sheet = client.open_by_key(SHEET_ID).sheet1

if sheet.row_count == 0 or sheet.cell(1, 1).value is None:
    sheet.append_row(["type", "attacker", "value", "attemptNum", "wasBlacklisted", "timestamp"])


print(f"Monitoring honeypot at: {CONTRACT_ADDRESS}")
print("Waiting for events...")


last_block = web3.eth.block_number
while True:
    try:
        current_block = web3.eth.block_number
        if current_block > last_block:
            logs = contract.events.AttemptDetailed.get_logs(from_block=last_block + 1, to_block=current_block)
            for log in logs:
                sheet.append_row([
                    "AttemptDetailed",
                    log.args.attacker,
                    log.args.value,
                    log.args.attemptNum,
                    str(log.args.wasBlacklisted),
                    log.args.timestamp
                ])
                print(f"Attempt: {log.args.attacker} | {log.args.value} wei")
            logs2 = contract.events.Caught.get_logs(from_block=last_block + 1, to_block=current_block)
            for log in logs2:
                sheet.append_row([
                    "Caught",
                    log.args.attacker,
                    "", "", "", log.args.timestamp
                ])
                print(f"Caught: {log.args.attacker}")
            last_block = current_block
        time.sleep(15)
    except Exception as e:
        print(f"Error: ", e)
        web3 = Web3(Web3.HTTPProvider(INFURA_URL))
        contract = web3.eth.contract(address=CONTRACT_ADDRESS, abi=ABI)
        time.sleep(15)

