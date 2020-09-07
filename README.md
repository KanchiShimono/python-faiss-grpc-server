# python-faiss-grpc-server

Python gRPC server for apploximate nearest neighbor by [Faiss](https://github.com/facebookresearch/faiss).

## Installation

You can install as package by pip install on repository root.

```sh
pip install .
```

## Usage

You can start gRPC server by running following command.

```sh
python python/faiss_grpc/main.py
```

## Examples

Client side code is under the `examples/client.py`.
You can run following command or directory running on interpreter.

```sh
cd examples
python client.py
```

## Development

### Generate python code

Following command will generate two python grpc code `faiss_pb2.py` and `faiss_pb2_grpc.py` under the `python/faiss_grpc/proto`.
If you update grpc definition `proto/faiss.proto`, you should regenerate at first.

```sh
make codegen
```

Then you have to fix import path in `faiss_pb2_grpc.py`.

```py
# Before
import faiss_pb2 as faiss__pb2
# After
import faiss_grpc.proto.faiss_pb2 as faiss__pb2
```
