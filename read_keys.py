from modules import config_store
print(f"Free Key: '{config_store.load_api_key()}'")
print(f"Pro Key: '{config_store.load_api_key_pro()}'")
