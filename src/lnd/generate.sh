#!/bin/sh

curl -o lightning.proto -s https://raw.githubusercontent.com/lightningnetwork/lnd/master/lnrpc/lightning.proto
curl -o router.proto -s https://raw.githubusercontent.com/lightningnetwork/lnd/master/lnrpc/routerrpc/router.proto

uv run --with grpcio-tools python -m grpc_tools.protoc   -I.   --python_out=.   --grpc_python_out=.   lightning.proto   router.proto

# Rewrite absolute imports to package-relative so these modules work when imported as src.lnd.*
for f in lightning_pb2_grpc.py router_pb2.py router_pb2_grpc.py; do
    sed -i -E 's/^import (lightning_pb2|router_pb2) as /from . import \1 as /' "$f"
done
