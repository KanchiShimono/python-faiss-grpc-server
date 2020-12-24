from concurrent import futures
from dataclasses import dataclass
from typing import List, Optional

import faiss
import grpc
import numpy as np
from faiss import Index

from faiss_grpc.proto.faiss_pb2 import (
    HeartbeatResponse,
    Neighbor,
    SearchByIdResponse,
    SearchResponse,
)
from faiss_grpc.proto.faiss_pb2_grpc import (
    FaissServiceServicer,
    add_FaissServiceServicer_to_server,
)


@dataclass(eq=True, frozen=True)
class ServerConfig:
    host: str = '[::]'
    port: int = 50051
    max_workers: int = 10


@dataclass(eq=True, frozen=True)
class FaissServiceConfig:
    nprobe: Optional[int] = None
    normalize_query: bool = False


class FaissServiceServicer(FaissServiceServicer):
    def __init__(self, index: Index, config: FaissServiceConfig) -> None:
        self.index = index
        self.config = config
        if self.config.nprobe:
            self.index.nprobe = self.config.nprobe

    def Search(self, request, context) -> SearchResponse:
        query = np.atleast_2d(np.array(request.query.val, dtype=np.float32))
        if query.shape[1] != self.index.d:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            msg = (
                'query vector dimension mismatch '
                f'expected {self.index.d} but passed {query.shape[1]}'
            )
            context.set_details(msg)
            return SearchResponse()

        if self.config.normalize_query:
            query = self.normalize(query)

        distances, ids = self.index.search(query, request.k)

        neighbors: List[Neighbor] = []
        for d, i in zip(distances[0], ids[0]):
            if i != -1:
                neighbors.append(Neighbor(id=i, score=d))

        return SearchResponse(neighbors=neighbors)

    def SearchById(self, request, context) -> SearchByIdResponse:
        request_id = request.id
        maximum_id = self.index.ntotal - 1
        if not (0 <= request_id <= maximum_id):
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            msg = f'request id must be 0 <= id <= {maximum_id}'
            context.set_details(msg)
            return SearchByIdResponse()

        query = self.index.reconstruct_n(request_id, 1)

        distances, ids = self.index.search(query, request.k + 1)

        neighbors: List[Neighbor] = []
        for d, i in zip(distances[0], ids[0]):
            if i not in [request_id, -1]:
                neighbors.append(Neighbor(id=i, score=d))

        return SearchByIdResponse(request_id=request_id, neighbors=neighbors)

    def Heartbeat(self, request, context) -> HeartbeatResponse:
        return HeartbeatResponse(message='OK')

    @staticmethod
    def normalize(vec: np.ndarray) -> np.ndarray:
        return vec / np.linalg.norm(vec, axis=1, keepdims=True)


class Server:
    def __init__(
        self,
        index_path: str,
        server_config: ServerConfig,
        service_config: FaissServiceConfig,
    ) -> None:
        index = faiss.read_index(index_path)
        self.server = grpc.server(
            futures.ThreadPoolExecutor(max_workers=server_config.max_workers)
        )
        add_FaissServiceServicer_to_server(
            FaissServiceServicer(index, service_config), self.server
        )
        self.server.add_insecure_port(
            f'{server_config.host}:{server_config.port}'
        )

    def serve(self) -> None:
        self.server.start()
        self.server.wait_for_termination()
