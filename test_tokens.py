import os
import sys

from modules import config_store
print("Token Summary:")
summary = config_store.get_token_summary()
print(summary)
print("---")
print("Latest Usage:")
print(config_store.get_token_history(5))
