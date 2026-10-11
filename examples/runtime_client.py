"""Model-free SDK client example; the same operations are available over MCP."""
import argparse
import json

from bokkio.sdk import Client

parser = argparse.ArgumentParser()
parser.add_argument("--state", required=True)
parser.add_argument("--policy", required=True)
parser.add_argument("--app")
args = parser.parse_args()
client = Client.from_policy(args.state, args.policy)
opened = client.open()
print(json.dumps(opened, ensure_ascii=False))
if args.app:
    print(json.dumps(client.call("desktop.observe", {"app": args.app}), ensure_ascii=False))
print(json.dumps(client.call("metrics.summary"), ensure_ascii=False))
# Keep the session open for subsequent CLI/MCP calls or close explicitly.
