import argparse
from argparse import Namespace
from typing import List, Union

import grpc
import numpy as np
from google.protobuf.empty_pb2 import Empty

import faiss_pb2  # isort:skip
import faiss_pb2_grpc  # isort:skip

VectorLike = Union[List[float], np.ndarray]


class GrpcClient:
    def __init__(self) -> None:
        channel = grpc.insecure_channel('localhost:50051')
        self._stub = faiss_pb2_grpc.FaissServiceStub(channel)

    @property
    def stub(self) -> faiss_pb2_grpc.FaissServiceStub:
        return self._stub

    def search(self, query: VectorLike, k: int) -> None:
        vec = faiss_pb2.Vector(val=query)
        req = faiss_pb2.SearchRequest(query=vec, k=k)
        res = self.stub.Search(req)

        for i, n in enumerate(res.neighbors):
            print(f'#{i}, id: {n.id}, score: {n.score}')

    def search_by_id(self, request_id: int, k: int) -> None:
        req = faiss_pb2.SearchByIdRequest(id=request_id, k=k)
        res = self.stub.SearchById(req)

        print(f'requested id {res.request_id}')
        for i, n in enumerate(res.neighbors):
            print(f'#{i}, id: {n.id}, score: {n.score}')

    def heatbeat(self) -> None:
        res = self.stub.Heatbeat(Empty())
        print(f'message {res.message}')


def heatbeat(_: Namespace) -> None:
    client = GrpcClient()
    client.heatbeat()


def search(args: Namespace) -> None:
    client = GrpcClient()
    query = np.ones(300, dtype=np.float32)
    client.search(query, args.k)


def search_by_id(args: Namespace) -> None:
    client = GrpcClient()
    client.search_by_id(args.id, args.k)


def run() -> None:
    parser = argparse.ArgumentParser(description='gRPC client example')
    sub_parser = parser.add_subparsers(title='subcommands')

    parser_heatbeat = sub_parser.add_parser('heatbeat', description='heatbeat')
    parser_heatbeat.set_defaults(handler=heatbeat)

    parser_search = sub_parser.add_parser(
        'search',
        description=(
            'search nearest neighbors of given query. '
            'in this example query is prepared as identity vector.'
        ),
    )
    parser_search.add_argument('k', type=int)
    parser_search.set_defaults(handler=search)

    parser_seach_by_id = sub_parser.add_parser(
        'search-by-id', description='search nearest neighbors of given id'
    )
    parser_seach_by_id.add_argument('id', type=int)
    parser_seach_by_id.add_argument('k', type=int)
    parser_seach_by_id.set_defaults(handler=search_by_id)

    args = parser.parse_args()

    if hasattr(args, 'handler'):
        args.handler(args)
    else:
        print('subcommand is required one of {heatbeat, search, search-by-id}')


if __name__ == "__main__":
    run()
