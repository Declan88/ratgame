import json
import sys
from direct.task.TaskManagerGlobal import taskMgr
from .remote_player import RemotePlayer
from steamworks import STEAMWORKS


class NetworkManager:
    def __init__(self, app):
        self.app = app
        self.remote_players = {}
        self.remote_steam_id = None

        try:
            self.steam = STEAMWORKS()
            self.steam.initialize()
            print("Steam P2P initialized successfully.")
            
            # Get and print local user's Steam ID instantly (no async lobby callbacks needed)
            local_steam_id = self.steam.Users.GetSteamID() if hasattr(self.steam, "Users") else self.steam.GetSteamID()
            print(f"Your Steam ID: {local_steam_id}")
            
            self.setup_networking_mode()
            
        except Exception as e:
            print(
                f"Steam initialization failed: {e}. Make sure Steam client is running."
            )
            self.steam = None

        if self.steam:
            taskMgr.add(self.poll_packets, "poll_network_task")

    def setup_networking_mode(self):
        print("\n--- Networking Setup ---")
        print("1. Act as Host (Wait for incoming P2P packets)")
        print("2. Connect to Host (Enter Host's Steam ID)")
        choice = input("Select an option (1 or 2): ").strip()

        if choice == "1":
            print("Hosting mode active. Waiting for incoming connections...")
        elif choice == "2":
            try:
                id_input = input("Paste Host's Steam ID: ").strip()
                self.remote_steam_id = int(id_input)
                print(f"Targeting Host Steam ID: {self.remote_steam_id}...")
                
                # Accept session / send initial handshake packet if supported
                if hasattr(self.steam, "Networking"):
                    self.steam.Networking.AcceptP2PSessionWithUser(self.remote_steam_id)
            except ValueError:
                print("Error: Invalid Steam ID. Must be a numeric value.")
        else:
            print("Invalid choice. Defaulting to Host mode...")

    def poll_packets(self, task):
        if not self.steam:
            return task.cont

        if hasattr(self.steam, "run_callbacks"):
            self.steam.run_callbacks()

        # Read incoming P2P packets directly from Steam network queue
        # if hasattr(self.steam, "Networking"):
        #     while packet := self.steam.Networking.ReadP2PSession(): # depends on wrapper implementation
        #         pass

        return task.cont

    def broadcast_position(self, pos, hpr):
        if not self.steam or not self.remote_steam_id:
            return

        payload = json.dumps(
            {"pos": [pos.x, pos.y, pos.z], "hpr": [hpr.x, hpr.y, hpr.z]}
        ).encode("utf-8")

        # Send P2P packet directly to the peer's Steam ID
        # if hasattr(self.steam, "Networking"):
        #     self.steam.Networking.SendP2PData(self.remote_steam_id, payload, len(payload), 0, 1)
        pass

    def handle_data(self, sender_id, data):
        if sender_id not in self.remote_players:
            self.remote_players[sender_id] = RemotePlayer(self.app, sender_id)

        parsed = json.loads(data.decode("utf-8"))
        if "pos" in parsed and "hpr" in parsed:
            self.remote_players[sender_id].update_transform(
                parsed["pos"], parsed["hpr"]
            )