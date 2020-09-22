import os
import tempfile
import unittest
from dataclasses import dataclass
from enum import Enum, unique
from typing import Any, List, Union

import faiss
import grpc
import grpc_testing
import numpy as np
from faiss import Index
from google.protobuf.empty_pb2 import Empty
from google.protobuf.pyext._message import MethodDescriptor
from grpc_testing._server._server import _Server

from faiss_grpc.faiss_server import (
    FaissServiceConfig,
    FaissServiceServicer,
    Server,
    ServerConfig,
)
from faiss_grpc.proto import faiss_pb2, faiss_pb2_grpc
from faiss_grpc.proto.faiss_pb2 import (
    HeatbeatResponse,
    Neighbor,
    SearchByIdRequest,
    SearchByIdResponse,
    SearchRequest,
    SearchResponse,
    Vector,
)

VectorLike = Union[List[float], np.ndarray]


@dataclass(frozen=True)
class FaissConfig:
    dim: int
    db_size: int
    nlist: int


@unique
class ServiceMethodDescriptor(Enum):
    search = 'Search'
    search_by_id = 'SearchById'
    heatbeat = 'Heatbeat'


class GrpcClientForTesting:
    def __init__(self) -> None:
        channel = grpc.insecure_channel('localhost:50051')
        self._stub = faiss_pb2_grpc.FaissServiceStub(channel)

    @property
    def stub(self) -> faiss_pb2_grpc.FaissServiceStub:
        return self._stub

    def search(self, query: VectorLike, k: int) -> SearchResponse:
        vec = faiss_pb2.Vector(val=query)
        req = faiss_pb2.SearchRequest(query=vec, k=k)
        return self.stub.Search(req)

    def search_by_id(self, request_id: int, k: int) -> SearchByIdResponse:
        req = faiss_pb2.SearchByIdRequest(id=request_id, k=k)
        return self.stub.SearchById(req)

    def heatbeat(self) -> HeatbeatResponse:
        return self.stub.Heatbeat(Empty())


class BaseTestCase(unittest.TestCase):
    FAISS_CONFIG: FaissConfig

    @classmethod
    def create_index(cls) -> Index:
        # following code is same as sample of faiss github wiki
        #   https://github.com/facebookresearch/faiss/wiki/Getting-started
        #   https://github.com/facebookresearch/faiss/wiki/Faster-search
        d = cls.FAISS_CONFIG.dim
        nb = cls.FAISS_CONFIG.db_size
        np.random.seed(1234)
        xb = np.random.random((nb, d)).astype('float32')
        xb[:, 0] += np.arange(nb) / 1000.0

        nlist = cls.FAISS_CONFIG.nlist
        quantizer = faiss.IndexFlatL2(d)
        index = faiss.IndexIVFFlat(quantizer, d, nlist)
        index.train(xb)
        index.add(xb)

        return index


class TestFaissServiceServicer(BaseTestCase):
    # FAISS_CONFIG is defined in BaseTestCase
    CONFIG: FaissServiceConfig
    CONFIG_NORM: FaissServiceConfig
    INDEX: Index
    SERVICE: Any
    SERVER: _Server
    SERVER_NORM: _Server

    @classmethod
    def setUpClass(cls) -> None:
        nprobe = 10
        cls.CONFIG = FaissServiceConfig(nprobe=nprobe, normalize_query=False)
        cls.CONFIG_NORM = FaissServiceConfig(
            nprobe=nprobe, normalize_query=True
        )
        cls.FAISS_CONFIG = FaissConfig(dim=64, db_size=100000, nlist=100)
        cls.INDEX = cls.create_index()
        cls.SERVICE = faiss_pb2.DESCRIPTOR.services_by_name['FaissService']
        # faiss index must be cloned, because index attribute will be changed
        # FaissServiceServicer constructor (e.g. nprobe)
        cls.SERVER = grpc_testing.server_from_dictionary(
            {
                cls.SERVICE: FaissServiceServicer(
                    faiss.clone_index(cls.INDEX), cls.CONFIG
                )
            },
            grpc_testing.strict_real_time(),
        )
        # server for normalize_query is True
        cls.SERVER_NORM = grpc_testing.server_from_dictionary(
            {
                cls.SERVICE: FaissServiceServicer(
                    faiss.clone_index(cls.INDEX), cls.CONFIG_NORM
                )
            },
            grpc_testing.strict_real_time(),
        )
        # set nprobe, after complete cloning index
        cls.INDEX.nprobe = nprobe

    def method_descriptor_by_name(
        self, method: ServiceMethodDescriptor
    ) -> MethodDescriptor:
        return self.SERVICE.methods_by_name[method.value]

    @staticmethod
    def to_neighbors(distances: np.ndarray, ids: np.ndarray) -> List[Neighbor]:
        neighbors: List[Neighbor] = []
        for d, i in zip(distances[0], ids[0]):
            if i != -1:
                neighbors.append(Neighbor(id=i, score=d))
        return neighbors

    def test_successful_Search(self) -> None:
        # k must be set large value,
        # becauseof avoiding to miss error case came from small nprobe value.
        # if both nprobe and k are set small, search result would be same, even
        # if failed to set nprobe on server side.
        k = 1000
        val = np.ones(self.FAISS_CONFIG.dim, dtype=np.float32)
        vector = Vector(val=val)
        request = SearchRequest(query=vector, k=k)
        rpc = self.SERVER.invoke_unary_unary(
            self.method_descriptor_by_name(ServiceMethodDescriptor.search),
            (),
            request,
            None,
        )

        distances, ids = self.INDEX.search(np.atleast_2d(val), k)
        expected = SearchResponse(neighbors=self.to_neighbors(distances, ids))

        response, _, code, _ = rpc.termination()

        self.assertEqual(response, expected)
        self.assertIs(code, grpc.StatusCode.OK)

    def test_failed_different_nprobe_Search(self) -> None:
        # k must be set large value,
        # becauseof avoiding to miss error case came from small nprobe value.
        # if both nprobe and k are set small, search result would be same, even
        # if failed to set nprobe on server side.
        k = 1000
        val = np.ones(self.FAISS_CONFIG.dim, dtype=np.float32)
        vector = Vector(val=val)
        request = SearchRequest(query=vector, k=k)
        rpc = self.SERVER.invoke_unary_unary(
            self.method_descriptor_by_name(ServiceMethodDescriptor.search),
            (),
            request,
            None,
        )

        # set different nprobe
        index = faiss.clone_index(self.INDEX)
        index.nprobe = 1
        distances, ids = index.search(np.atleast_2d(val), k)
        unexpected = SearchResponse(
            neighbors=self.to_neighbors(distances, ids)
        )

        response, _, code, _ = rpc.termination()

        self.assertNotEqual(response, unexpected)
        self.assertIs(code, grpc.StatusCode.OK)

    def test_successful_normalize_query_Search(self) -> None:
        # k must be set large value,
        # becauseof avoiding to miss error case came from small nprobe value.
        # if both nprobe and k are set small, search result would be same, even
        # if failed to set nprobe on server side.
        k = 1000
        val = np.ones(self.FAISS_CONFIG.dim, dtype=np.float32)
        vector = Vector(val=val)
        request = SearchRequest(query=vector, k=k)
        # calling server set normalize_query is True
        rpc = self.SERVER_NORM.invoke_unary_unary(
            self.method_descriptor_by_name(ServiceMethodDescriptor.search),
            (),
            request,
            None,
        )

        # normalize query vector
        norm_val = val / np.linalg.norm(val)
        distances, ids = self.INDEX.search(np.atleast_2d(norm_val), k)
        expected = SearchResponse(neighbors=self.to_neighbors(distances, ids))

        response, _, code, _ = rpc.termination()

        self.assertEqual(response, expected)
        self.assertIs(code, grpc.StatusCode.OK)

    def test_failed_illegal_query_dimension_Search(self) -> None:
        k = 10
        val = np.ones(self.FAISS_CONFIG.dim * 2, dtype=np.float32)
        vector = Vector(val=val)
        request = SearchRequest(query=vector, k=k)
        rpc = self.SERVER.invoke_unary_unary(
            self.method_descriptor_by_name(ServiceMethodDescriptor.search),
            (),
            request,
            None,
        )

        response, _, code, details = rpc.termination()

        self.assertRegex(
            details,
            f'query vector dimension mismatch expected '
            f'{self.FAISS_CONFIG.dim} but passed {self.FAISS_CONFIG.dim*2}',
        )
        # exptected empty SearchResponse
        self.assertEqual(response, SearchResponse())
        self.assertIs(code, grpc.StatusCode.INVALID_ARGUMENT)

    def test_successful_SearchById(self) -> None:
        # k must be set large value,
        # becauseof avoiding to miss error case came from small nprobe value.
        # if both nprobe and k are set small, search result would be same, even
        # if failed to set nprobe on server side.
        request_id = 0
        k = 1000
        request = SearchByIdRequest(id=request_id, k=k)
        rpc = self.SERVER.invoke_unary_unary(
            self.method_descriptor_by_name(
                ServiceMethodDescriptor.search_by_id
            ),
            (),
            request,
            None,
        )

        query = self.INDEX.reconstruct_n(request_id, 1)
        # search k + 1 considering remove request_id itself
        distances, ids = self.INDEX.search(query, k + 1)
        neighbors = [
            n for n in self.to_neighbors(distances, ids) if n.id != request_id
        ]
        expected = SearchByIdResponse(
            request_id=request_id, neighbors=neighbors
        )

        response, _, code, _ = rpc.termination()

        self.assertEqual(response, expected)
        self.assertIs(code, grpc.StatusCode.OK)

    def test_failed_unknown_id_SearchById(self) -> None:
        # set unknown id
        request_id = self.FAISS_CONFIG.db_size * 2
        k = 10
        request = SearchByIdRequest(id=request_id, k=k)
        rpc = self.SERVER.invoke_unary_unary(
            self.method_descriptor_by_name(
                ServiceMethodDescriptor.search_by_id
            ),
            (),
            request,
            None,
        )

        response, _, code, details = rpc.termination()

        self.assertRegex(
            details,
            f'request id must be 0 <= id <= {self.FAISS_CONFIG.db_size-1}',
        )
        # exptected empty SearchByIdResponse
        self.assertEqual(response, SearchByIdResponse())
        self.assertIs(code, grpc.StatusCode.INVALID_ARGUMENT)

    def test_successful_Heatbeat(self) -> None:
        request = Empty()
        rpc = self.SERVER.invoke_unary_unary(
            self.method_descriptor_by_name(ServiceMethodDescriptor.heatbeat),
            (),
            request,
            None,
        )

        response, _, code, _ = rpc.termination()

        self.assertEqual(HeatbeatResponse(message='OK'), response)
        self.assertIs(code, grpc.StatusCode.OK)


class TestServer(BaseTestCase):
    # FAISS_CONFIG is defined in BaseTestCase
    SERVER_CONFIG: ServerConfig
    SERVICE_CONFIG: FaissServiceConfig
    CLIENT: GrpcClientForTesting
    SERVER: Server

    @classmethod
    def setUpClass(cls) -> None:
        cls.SERVER_CONFIG = ServerConfig()
        cls.SERVICE_CONFIG = FaissServiceConfig(nprobe=10)
        cls.FAISS_CONFIG = FaissConfig(dim=64, db_size=100000, nlist=100)
        cls.CLIENT = GrpcClientForTesting()

        index = cls.create_index()
        with tempfile.TemporaryDirectory() as temp_dir:
            index_path = os.path.join(temp_dir, 'index.faiss')
            faiss.write_index(index, index_path)
            cls.SERVER = Server(
                index_path=index_path,
                server_config=cls.SERVER_CONFIG,
                service_config=cls.SERVICE_CONFIG,
            )

        cls.SERVER.server.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.SERVER.server.stop(None)

    def test_serve_search(self) -> None:
        k = 10
        response = self.CLIENT.search(
            np.ones(self.FAISS_CONFIG.dim, dtype=np.float32), k=k
        )
        self.assertEqual(len(response.neighbors), k)

    def test_serve_search_by_id(self) -> None:
        request_id = 0
        k = 10
        response = self.CLIENT.search_by_id(request_id=request_id, k=k)
        self.assertEqual(response.request_id, request_id)
        self.assertEqual(len(response.neighbors), k)

    def test_serve_heatbeat(self) -> None:
        response = self.CLIENT.heatbeat()
        self.assertEqual(response, HeatbeatResponse(message='OK'))


if __name__ == "__main__":
    unittest.main(verbosity=2)
