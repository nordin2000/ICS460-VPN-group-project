import json
import getpass
import urllib.request
import urllib.error
from urllib.parse import quote

API_URL = "https://api.netbird.io/api"

TOKEN = getpass.getpass("Enter NetBird API token: ")


def connect(endpoint):
    headers = {
        "Authorization": "Token " + TOKEN,
        "Accept": "application/json"
    }

    request = urllib.request.Request(
        API_URL + endpoint,
        headers=headers,
        method="GET"
    )

    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            result = response.read().decode()
            return json.loads(result) if result else {}

    except urllib.error.HTTPError as error:
        print("API Error:", error.code)
        print(error.read().decode())
        return None

    except urllib.error.URLError as error:
        print("Connection Error:", error.reason)
        return None

    except json.JSONDecodeError:
        print("Could not read the API response.")
        return None

def load_config():
    try:
        with open("user_config.json", "r") as file:
            return json.load(file)

    except FileNotFoundError:
        print("user_config.json was not found.")
        return None

    except json.JSONDecodeError:
        print("There is an error in user_config.json.")
        return None

def get_users():
    return connect("/users")


def get_groups():
    return connect("/groups")


def get_peers():
    return connect("/peers")


def get_museum_role(user, peers, config):
    group_ids = {
        "Staff": config["groups"]["staff"]["peer_group_id"],
        "Volunteers": config["groups"]["volunteers"]["peer_group_id"]
    }

    assigned_groups = set()

    user_groups = user.get("auto_groups", [])

    for group in user_groups:
        group_id = group.get("id") if isinstance(group, dict) else group

        for role, configured_id in group_ids.items():
            if group_id == configured_id:
                assigned_groups.add(role)

    user_id = user.get("id")

    for peer in peers:
        if peer.get("user_id") != user_id:
            continue

        peer_groups = peer.get("groups", [])

        for group in peer_groups:
            group_id = group.get("id") if isinstance(group, dict) else group

            for role, configured_id in group_ids.items():
                if group_id == configured_id:
                    assigned_groups.add(role)

    if len(assigned_groups) == 1:
        return assigned_groups.pop()

    if len(assigned_groups) > 1:
        return "Multiple groups: " + ", ".join(sorted(assigned_groups))

    return "Not assigned"

def list_users():
    users = get_users()
    peers = get_peers()
    config = load_config()

    if not isinstance(users, list):
        print("Could not retrieve users.")
        return

    if not isinstance(peers, list):
        print("Could not retrieve devices.")
        return

    if config is None:
        return

    print("\n===== Museum VPN Users =====")

    for user in users:
        museum_role = get_museum_role(user, peers, config)

        print("----------------------------")
        print("Name:", user.get("name", "N/A"))
        print("Email:", user.get("email", "N/A"))
        print("Museum Role:", museum_role)
        print("Account Status:", user.get("status", "N/A"))
        print("Blocked:", user.get("is_blocked", "N/A"))

def view_groups():
    groups = get_groups()
    config = load_config()

    if not isinstance(groups, list):
        print("Could not retrieve groups.")
        return

    if config is None:
        return

    print("\n===== Museum VPN Groups =====")

    for group in groups:
        print("\nGroup:", group.get("name", "Unknown"))
        print("Group ID:", group.get("id", "N/A"))

        members = group.get("peers", [])

        if members:
            print("Assigned Devices:")

            for peer in members:
                if isinstance(peer, dict):
                    print(" -", peer.get("name", "Unknown device"))
                else:
                    print(" -", peer)
        else:
            print(" - No devices assigned")

    print("\n===== Configured Museum Roles =====")

    for key, value in config["groups"].items():
        print(
            value["name"],
            ":",
            value["peer_group_id"]
        )


def check_user_access():
    email = input("\nEnter the user's email: ").strip().lower()

    users = get_users()
    peers = get_peers()
    config = load_config()

    if not isinstance(users, list):
        print("Could not retrieve users.")
        return

    if not isinstance(peers, list):
        print("Could not retrieve devices.")
        return

    if config is None:
        return

    user = next(
        (
            u for u in users
            if (u.get("email") or "").lower() == email
        ),
        None
    )

    if user is None:
        print("User not found.")
        return

    museum_role = get_museum_role(user, peers, config)

    print("\n===== User Access Information =====")
    print("Name:", user.get("name", "N/A"))
    print("Email:", user.get("email", "N/A"))
    print("Museum Role:", museum_role)
    print("Account Status:", user.get("status", "N/A"))

    print(
        "Account Blocked:",
        "YES" if user.get("is_blocked") else "NO"
    )

    user_peers = [
        peer for peer in peers
        if peer.get("user_id") == user.get("id")
    ]

    if not user_peers:
        print("\nNo registered devices found for this user.")
        print("Museum group access cannot be determined yet.")
        return

    for peer in user_peers:
        print("\n----------------------------")
        print("Device:", peer.get("name", "Unknown"))
        print("VPN IP:", peer.get("ip", "N/A"))
        print("Connected:", peer.get("connected", "N/A"))

        peer_groups = peer.get("groups", [])

        print("Assigned Groups:")

        if peer_groups:
            for group in peer_groups:
                if isinstance(group, dict):
                    print(" -", group.get("name", group.get("id", "Unknown")))
                else:
                    print(" -", group)
        else:
            print(" - None")

        peer_id = peer.get("id")

        if not peer_id:
            print("Could not check accessible devices: missing peer ID.")
            continue

        accessible = connect(
            "/peers/" + quote(peer_id, safe="")
            + "/accessible-peers"
        )

        print("\nAccessible VPN Devices:")

        if isinstance(accessible, list) and accessible:
            for destination in accessible:
                print(
                    " -",
                    destination.get("name", "Unknown"),
                    "| IP:",
                    destination.get("ip", "N/A")
                )

        elif isinstance(accessible, list):
            print(" - No accessible peers reported.")

        else:
            print("Could not retrieve accessible peers.")

def main():
    while True:
        print("\n===== Museum VPN User Management =====")
        print("1. List Users")
        print("2. View Groups")
        print("3. Check User Access")
        print("4. Exit")

        choice = input("\nChoose an option: ").strip()

        if choice == "1":
            list_users()

        elif choice == "2":
            view_groups()

        elif choice == "3":
            check_user_access()

        elif choice == "4":
            print("Goodbye!")
            break

        else:
            print("Invalid choice. Try again.")

if __name__ == "__main__":
    main()
