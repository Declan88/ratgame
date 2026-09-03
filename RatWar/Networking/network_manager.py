import json
import os
import sys
import ctypes

# --- FORCE LOAD STEAM API DLL GLOBALLY FIRST ---
def load_steam_api_dll():
    possible_paths = [
        os.path.join(os.path.dirname(__file__), "..", "steam_api64.dll"),
        os.path.join(os.path.dirname(__file__), "steam_api64.dll"),
        r"E:\Python\RatWar\steam_api64.dll"
    ]
    
    loaded = False
    for path in possible_paths:
        abs_path = os.path.abspath(path)
        if os.path.exists(abs_path):
            try:
                ctypes.CDLL(abs_path, mode=ctypes.RTLD_GLOBAL)
                print(f"Successfully pre-loaded steam_api64.dll from: {abs_path}")
                loaded = True
                break
            except Exception as e:
                print(f"Failed loading {abs_path}: {e}")
                
    if not loaded:
        print("CRITICAL ERROR: Could not find or load steam_api64.dll!")
        sys.exit(1)

load_steam_api_dll()
# -----------------------------------------------

import py_steam_net
from direct.task.TaskManagerGlobal import taskMgr
from .remote_player import RemotePlayer


class NetworkManager:
    def __init__(self, app):
        self.app = app
        self.remote_players = {}
        self.current_lobby_id = None
        self.last_pos = None
        self.last_hpr = None

        try:
            self.client = py_steam_net.PySteamClient()
            self.client.init(480)
            print(f"Steam P2P initialized successfully. Ready: {self.client.is_ready()}")
            
            self.local_steam_id = self.client.own_steam_id()
            print(f"Your Steam ID: {self.local_steam_id}")

            self.client.set_message_recv_callback(self.handle_data)
            self.client.set_lobby_changed_callback(self.on_lobby_changed)

            self.setup_networking_mode()

        except Exception as e:
            print(f"Steam initialization failed: {e}. Make sure Steam client is running.")
            self.client = None

        if self.client:
            taskMgr.add(self.poll_packets, "poll_network_task")
            taskMgr.add(self.broadcast_transform_task, "broadcast_transform_task")

    def print_session_roster(self):
        if not self.current_lobby_id:
            return
        try:
            members = self.client.get_lobby_members(self.current_lobby_id)
            if not members:
                return
            
            host_id = members[0]  # First member is the lobby owner/host
            print("\n===============================")
            print("       SESSION ROSTER          ")
            print("===============================")
            for member_id in members:
                role = "HOST" if member_id == host_id else "CLIENT"
                is_local = " (You)" if member_id == self.local_steam_id else ""
                print(f" - Steam ID: {member_id}{is_local} [{role}]")
            print("===============================\n")
        except Exception as e:
            print(f"Error printing session roster: {e}")

    def on_lobby_created(self, lobby_id, error=None):
        if error:
            print(f"\n--> Failed to create lobby: {error}")
        else:
            self.current_lobby_id = lobby_id
            print(f"\n--> SUCCESS! Lobby Created ID: {self.current_lobby_id}")
            print("Hosting game session...")
            self.print_session_roster()

    def on_lobby_joined(self, lobby_id, error=None):
        if error:
            print(f"\n--> Failed to join lobby: {error}")
        else:
            self.current_lobby_id = lobby_id
            print(f"\n--> SUCCESS! Joined Lobby ID: {self.current_lobby_id}")
            self.print_session_roster()

    def on_lobby_changed(self, lobby_id, user_changed, making_change, member_state_change):
        print(f"\n[Lobby Update] Lobby ID: {lobby_id}, User: {user_changed}, State Change: {member_state_change}")
        if self.current_lobby_id:
            self.print_session_roster()

    def setup_networking_mode(self):
        print("\n--- Scanning for Open Lobbies ---")
        
        def handle_lobby_list(lobbies, error):
            if error:
                print(f"Failed to request lobby list: {error}")
                print("Hosting a new lobby instead...")
                self.client.create_lobby(2, 4, self.on_lobby_created)
                return

            open_lobby_id = None
            if lobbies:
                for l_id in lobbies:
                    try:
                        members = self.client.get_lobby_members(l_id)
                        if members and len(members) < 4:
                            open_lobby_id = l_id
                            break
                    except Exception:
                        continue

            if open_lobby_id:
                print(f"Found open lobby {open_lobby_id}. Joining automatically...")
                self.client.join_lobby(open_lobby_id, self.on_lobby_joined)
            else:
                print("No open lobbies found. Hosting a new lobby...")
                self.client.create_lobby(2, 4, self.on_lobby_created)

        try:
            self.client.get_lobby_list(handle_lobby_list)
        except Exception as e:
            print(f"Error initiating lobby list request: {e}")
            self.client.create_lobby(2, 4, self.on_lobby_created)

    def poll_packets(self, task):
        if not self.client:
            return task.cont

        self.client.run_callbacks()
        return task.cont

    def broadcast_transform_task(self, task):
        if not self.client or not self.current_lobby_id or not hasattr(self.app, "player"):
            return task.cont

        player_node = getattr(self.app.player, "node", getattr(self.app.player, "np", None))
        if not player_node:
            return task.cont

        current_pos = player_node.getPos()
        current_hpr = player_node.getHpr()

        if current_pos != self.last_pos or current_hpr != self.last_hpr:
            payload = json.dumps({
                "pos": [current_pos.x, current_pos.y, current_pos.z],
                "hpr": [current_hpr.x, current_hpr.y, current_hpr.z]
            }).encode("utf-8")

            try:
                members = self.client.get_lobby_members(self.current_lobby_id)
                for member_id in members:
                    if member_id != self.local_steam_id:
                        self.client.send_message_to(member_id, 2, 0, payload)
            except Exception:
                pass

            self.last_pos = current_pos
            self.last_hpr = current_hpr

        return task.cont

    def handle_data(self, sender_id, ch, msg_bytes):
        if sender_id not in self.remote_players:
            print(f"\n--> Discovered peer in lobby: {sender_id}")
            self.remote_players[sender_id] = RemotePlayer(self.app, sender_id)

        try:
            parsed = json.loads(msg_bytes.decode("utf-8"))
            if "pos" in parsed and "hpr" in parsed:
                self.remote_players[sender_id].update_transform(
                    parsed["pos"], parsed["hpr"]
                )
        except Exception as e:
            print(f"Error parsing incoming packet from {sender_id}: {e}")