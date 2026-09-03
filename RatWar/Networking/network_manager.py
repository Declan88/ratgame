import json
from direct.task.TaskManagerGlobal import taskMgr
from .remote_player import RemotePlayer
from steamworks import STEAMWORKS


class NetworkManager:
    def __init__(self, app):
        self.app = app
        self.remote_players = {}
        self.current_lobby_id = None

        try:
            self.steam = STEAMWORKS()
            self.steam.initialize()
            print("Steam P2P initialized successfully.")
            
            # Run lobby check right after successful initialization
            self.setup_lobby()
            
        except Exception as e:
            print(
                f"Steam initialization failed: {e}. Make sure Steam client is running."
            )
            self.steam = None

        if self.steam:
            taskMgr.add(self.poll_packets, "poll_network_task")

    def setup_lobby(self):
        """Checks for an active lobby or creates a new one if none exist."""
        # Note: steamworks-py handles lobby searches via Matchmaking callbacks. 
        # For a simplified setup, you can attempt to join a known lobby ID 
        # or implement a request list flow. If starting fresh, we create a public lobby.
        
        # Example: Requesting lobby list (ensure 'RequestLobbyList' is in your methods.py if used)
        # For simplicity, if no active lobby handler is cached, create one:
        print("Creating a new Steam lobby...")
        # k_ELobbyTypePublic = 0, Max members = 4
        self.steam.Matchmaking.CreateLobby(0, 4)

    def poll_packets(self, task):
        if not self.steam:
            return task.cont

        # Check Steam network queue for incoming data packets every frame
        # while packet := self.steam.networking.read_p2p_packet():
        #     self.handle_data(packet['sender'], packet['data'])

        return task.cont

    def broadcast_position(self, pos, hpr):
        if not self.steam:
            return

        payload = json.dumps(
            {"pos": [pos.x, pos.y, pos.z], "hpr": [hpr.x, hpr.y, hpr.z]}
        ).encode("utf-8")

        # Send data unreliably to connected session members
        # for steam_id in self.get_active_peers():
        #     self.steam.networking.send_p2p_packet(steam_id, payload, 0, 1)
        pass

    def handle_data(self, sender_id, data):
        if sender_id not in self.remote_players:
            self.remote_players[sender_id] = RemotePlayer(self.app, sender_id)

        parsed = json.loads(data.decode("utf-8"))
        if "pos" in parsed and "hpr" in parsed:
            self.remote_players[sender_id].update_transform(
                parsed["pos"], parsed["hpr"]
            )