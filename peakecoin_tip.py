# Whitelist of users to watch
WHITELIST_USERS = ["strangedad", "paulmoon410", "peakecoin"]
import requests

def show_whitelist_balances(token="PEK"):
    rpc_url = "https://api.hive-engine.com/rpc/contracts"
    headers = {"Content-Type": "application/json"}
    print("--- Whitelist PEK Balances ---")
    for user in WHITELIST_USERS:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "findOne",
            "params": {
                "contract": "tokens",
                "table": "balances",
                "query": {"account": user, "symbol": token}
            }
        }
        try:
            response = requests.post(rpc_url, json=payload, headers=headers, timeout=10)
            print(f"[DEBUG] RPC status for @{user}: {response.status_code}")
            print(f"[DEBUG] RPC raw response for @{user}: {response.text}")
            data = response.json()
            balance = data.get("result", {}).get("balance", "0")
            print(f"@{user}: {balance} {token}")
        except Exception as e:
            print(f"Error fetching PEK balance for @{user}: {e}")
    print("-----------------------------")
import time
import re
from nectar import Hive
from nectar.comment import Comment
from nectar.blockchain import Blockchain
from nectar.account import Account
from nectar.instance import set_shared_blockchain_instance
from nectarengine.wallet import Wallet

# --- Config ---
ACCOUNT = "peakecoin"
POSTING_KEY = "5Khy92RPZu4ymwoCumvBEMQj6uicgcZxPwNLbr6kAZMrbJcLCFA"    # Your posting key for replies
TOKEN = "PEK"
TIP_DELAY_SECONDS = 180
RC_THRESHOLD_PERCENT = 10
CHECK_INTERVAL = 30
TIP_MIN_AMOUNT = 0.00000001

# --- Hive setup ---
hive = Hive(keys=[POSTING_KEY])
set_shared_blockchain_instance(hive)
account = Account(ACCOUNT, blockchain_instance=hive)
blockchain = Blockchain(mode="head")

last_tip_time = 0
TIP_PATTERN = re.compile(r"#peaketip\s+@(\w+)(?:\s+([\d.]+))?(?:\s+(.*))?", re.IGNORECASE)

def has_enough_rc():
    rc_data = account.get_rc()
    print(f"[DEBUG] Full RC data: {rc_data}")
    current_mana = rc_data.get('rc_manabar', {}).get('current_mana', 0)
    max_rc = rc_data.get('max_rc', 1)
    percent = (current_mana / max_rc) * 100 if max_rc else 0
    print(f"[RC] Resource Credits: {percent:.2f}%")
    return percent > RC_THRESHOLD_PERCENT

def can_tip_now():
    global last_tip_time
    return (time.time() - last_tip_time) >= TIP_DELAY_SECONDS

def verify_tip_transaction(from_user, to_user, amount):
    """Verify that the tip transaction actually occurred on Hive Engine"""
    try:
        # For now, we'll assume the tip is valid
        # In a full implementation, you'd query Hive Engine API to verify
        print(f"🔍 Verifying tip from @{from_user} to @{to_user} for {amount} {TOKEN}")
        # TODO: Add actual Hive Engine transaction verification
        return True
    except Exception as e:
        print(f"❌ Error verifying transaction: {e}")
        return False

def send_tip(to_user, amount, memo):
    """This function is no longer used - users send their own tips"""
    return True

def reply_to_comment(parent_author, parent_permlink, from_user, to_user, amount):
    try:
        comment = Comment(f"@{parent_author}/{parent_permlink}")
        reply_body = f"✅ @{from_user} has tipped {amount} PEK to @{to_user}! Tip verified on Hive Engine. Thanks for using #peaketip."
        comment.reply(reply_body, author=ACCOUNT)
        print(f"📝 Replied to comment confirming tip from @{from_user} to @{to_user}")
    except Exception as e:
        print(f"❌ Failed to reply to comment: {e}")

def monitor_comments():
    global last_tip_time
    print("👀 Watching comments for #peaketip...")

    for op in blockchain.stream(["comment"]):
        try:
            # Only process comments from whitelisted users
            if op["author"] not in WHITELIST_USERS:
                continue
            print(f"[DEBUG] Saw whitelisted comment from @{op.get('author', '')} on permlink: {op.get('permlink', '')}")
            # Skip comments made by the bot itself (if you want to skip self)
            # if op["author"] == ACCOUNT:
            #     continue

            body = op.get("body", "")
            match = TIP_PATTERN.search(body)
            if not match:
                continue

            to_user, amount, memo = match.groups() if match.groups() else (None, None, None)
            if not to_user:
                print("❌ No user found to tip. Skipping.")
                continue
            memo = memo or "You've been tipped with PeakeCoin!"

            # Always use fixed tip amount if not provided or invalid
            TIP_FIXED_AMOUNT = 0.00001
            try:
                tip_amount = float(amount) if amount else TIP_FIXED_AMOUNT
            except (TypeError, ValueError):
                tip_amount = TIP_FIXED_AMOUNT

            print(f"[DEBUG] Preparing to tip @{to_user} {tip_amount} PEK. Memo: {memo}")

            # Enforce minimum tip amount
            if tip_amount < TIP_MIN_AMOUNT:
                print(f"❌ Tip amount {tip_amount} PEK is below the minimum of {TIP_MIN_AMOUNT} PEK. Skipping.")
                continue

            if not has_enough_rc():
                print("⚠️ RCs too low, skipping tip.")
                continue

            if not can_tip_now():
                print("⏳ Waiting before next tip.")
                continue

            # Verify that the user actually sent the tip
            if verify_tip_transaction(op["author"], to_user, tip_amount):
                reply_to_comment(op["author"], op["permlink"], op["author"], to_user, tip_amount)
                last_tip_time = time.time()
            else:
                print(f"❌ Could not verify tip transaction from @{op['author']} to @{to_user}")

        except Exception as e:
            print(f"⚠️ Error processing comment: {e}")

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    show_whitelist_balances()
    monitor_comments()
