import json
import time
import os
import gspread

from web3 import Web3
from dotenv import load_dotenv
from oauth2client.service_account import ServiceAccountCredentials


load_dotenv()

CONTRACT_ADDRESS = os.getenv('CONTRACT_ADDRESS')
INFURA_URL = os.getenv('INFURA_URL')
SHEET_ID = os.getenv('SHEET_ID')
GOOGLE_CREDS_JSON = os.getenv("GOOGLE_CREDS_JSON")

creds_dict = json.loads(GOOGLE_CREDS_JSON)


# ABI (skrót — tylko potrzebne eventy)
ABI = [
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "address", "name": "from", "type": "address"},
            {"indexed": False, "internalType": "uint256", "name": "value", "type": "uint256"}
        ],
        "name": "Bait",
        "type": "event"
    }
]

#Web3
web3 = Web3(Web3.HTTPProvider(INFURA_URL))
contract = web3.eth.contract(address=CONTRACT_ADDRESS, abi=ABI)

#Google sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open_by_key(SHEET_ID).sheet1

if sheet.row_count == 0 or sheet.cell(1, 1).value is None:
    sheet.append_row(["attacker", "value", "timestamp"])


print(f"Monitoring honeypot at: {CONTRACT_ADDRESS}")
print("Waiting for events...")


last_block = web3.eth.block_number
while True:
    try:
        current_block = web3.eth.block_number
        if current_block > last_block:
            logs = contract.events.Bait.get_logs(from_block=last_block + 1, to_block=current_block)
            for log in logs:
                sheet.append_row([
                    log.args['from'],
                    log.args['value'],
                    log.blockNumber
                ])
                print(f"Attempt: {log.args['from']} | {log.args['value']} wei")
            last_block = current_block
        time.sleep(60*30)
    except Exception as e:
        print(f"Error: ", e)
        web3 = Web3(Web3.HTTPProvider(INFURA_URL))
        contract = web3.eth.contract(address=CONTRACT_ADDRESS, abi=ABI)
        time.sleep(60*30)
        continue
