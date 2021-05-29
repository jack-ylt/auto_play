import asyncio

g_queue = asyncio.Queue()
g_event = asyncio.Event()
g_found = dict()
g_hand_lock = asyncio.Lock()
g_player_lock = asyncio.Lock()


