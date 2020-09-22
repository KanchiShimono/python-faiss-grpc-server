import unittest
from dataclasses import dataclass
from enum import Enum, unique
from typing import List

import faiss
import grpc
import grpc_testing
import numpy as np
from faiss import Index
from google.protobuf.empty_pb2 import Empty
from google.protobuf.pyext._message import MethodDescriptor

from faiss_grpc.faiss_server import FaissServiceConfig, FaissServiceServicer
from faiss_grpc.proto import faiss_pb2
from faiss_grpc.proto.faiss_pb2 import (
    HeatbeatResponse,
    Neighbor,
    SearchByIdRequest,
    SearchByIdResponse,
    SearchRequest,
    SearchResponse,
    Vector,
)


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


class TestFaissServiceServicer(unittest.TestCase):
    def setUp(self) -> None:
        nprobe = 10
        self.config = FaissServiceConfig(nprobe=nprobe, normalize_query=False)
        self.config_norm = FaissServiceConfig(
            nprobe=nprobe, normalize_query=True
        )
        self.faiss_config = FaissConfig(dim=64, db_size=100000, nlist=100)
        self.index = self.create_index()
        self.service = faiss_pb2.DESCRIPTOR.services_by_name['FaissService']
        # faiss index must be cloned, because index attribute will be changed
        # FaissServiceServicer constructor (e.g. nprobe)
        self.server = grpc_testing.server_from_dictionary(
            {
                self.service: FaissServiceServicer(
                    faiss.clone_index(self.index), self.config
                )
            },
            grpc_testing.strict_real_time(),
        )
        self.server_norm = grpc_testing.server_from_dictionary(
            {
                self.service: FaissServiceServicer(
                    faiss.clone_index(self.index), self.config_norm
                )
            },
            grpc_testing.strict_real_time(),
        )
        # set nprobe, after complete cloning index
        self.index.nprobe = nprobe

    def method_descriptor_by_name(
        self, method: ServiceMethodDescriptor
    ) -> MethodDescriptor:
        return self.service.methods_by_name[method.value]

    def create_index(self) -> Index:
        # following code is same as sample of faiss github wiki
        #   https://github.com/facebookresearch/faiss/wiki/Getting-started
        #   https://github.com/facebookresearch/faiss/wiki/Faster-search
        d = self.faiss_config.dim
        nb = self.faiss_config.db_size
        np.random.seed(1234)
        xb = np.random.random((nb, d)).astype('float32')
        xb[:, 0] += np.arange(nb) / 1000.0

        nlist = self.faiss_config.nlist
        quantizer = faiss.IndexFlatL2(d)
        index = faiss.IndexIVFFlat(quantizer, d, nlist)
        index.train(xb)
        index.add(xb)

        return index

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
        val = np.ones(self.faiss_config.dim, dtype=np.float32)
        vector = Vector(val=val)
        request = SearchRequest(query=vector, k=k)
        rpc = self.server.invoke_unary_unary(
            self.method_descriptor_by_name(ServiceMethodDescriptor.search),
            (),
            request,
            None,
        )

        distances, ids = self.index.search(np.atleast_2d(val), k)
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
        val = np.ones(self.faiss_config.dim, dtype=np.float32)
        vector = Vector(val=val)
        request = SearchRequest(query=vector, k=k)
        rpc = self.server.invoke_unary_unary(
            self.method_descriptor_by_name(ServiceMethodDescriptor.search),
            (),
            request,
            None,
        )

        # set different nprobe
        index = faiss.clone_index(self.index)
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
        val = np.ones(self.faiss_config.dim, dtype=np.float32)
        vector = Vector(val=val)
        request = SearchRequest(query=vector, k=k)
        # calling server set normalize_query is True
        rpc = self.server_norm.invoke_unary_unary(
            self.method_descriptor_by_name(ServiceMethodDescriptor.search),
            (),
            request,
            None,
        )

        # normalize query vector
        norm_val = val / np.linalg.norm(val)
        distances, ids = self.index.search(np.atleast_2d(norm_val), k)
        expected = SearchResponse(neighbors=self.to_neighbors(distances, ids))

        response, _, code, _ = rpc.termination()

        self.assertEqual(response, expected)
        self.assertIs(code, grpc.StatusCode.OK)

    def test_failed_illegal_query_dimension_Search(self) -> None:
        k = 10
        val = np.ones(self.faiss_config.dim * 2, dtype=np.float32)
        vector = Vector(val=val)
        request = SearchRequest(query=vector, k=k)
        rpc = self.server.invoke_unary_unary(
            self.method_descriptor_by_name(ServiceMethodDescriptor.search),
            (),
            request,
            None,
        )

        response, _, code, details = rpc.termination()

        self.assertRegex(
            details,
            f'query vector dimension mismatch expected '
            f'{self.faiss_config.dim} but passed {self.faiss_config.dim*2}',
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
        rpc = self.server.invoke_unary_unary(
            self.method_descriptor_by_name(
                ServiceMethodDescriptor.search_by_id
            ),
            (),
            request,
            None,
        )

        query = self.index.reconstruct_n(request_id, 1)
        # search k + 1 considering remove request_id itself
        distances, ids = self.index.search(query, k + 1)
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
        request_id = self.faiss_config.db_size * 2
        k = 10
        request = SearchByIdRequest(id=request_id, k=k)
        rpc = self.server.invoke_unary_unary(
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
            f'request id must be 0 <= id <= {self.faiss_config.db_size-1}',
        )
        # exptected empty SearchByIdResponse
        self.assertEqual(response, SearchByIdResponse())
        self.assertIs(code, grpc.StatusCode.INVALID_ARGUMENT)

    def test_successful_Heatbeat(self) -> None:
        request = Empty()
        rpc = self.server.invoke_unary_unary(
            self.method_descriptor_by_name(ServiceMethodDescriptor.heatbeat),
            (),
            request,
            None,
        )

        response, _, code, _ = rpc.termination()

        self.assertEqual(HeatbeatResponse(message='OK'), response)
        self.assertIs(code, grpc.StatusCode.OK)


if __name__ == "__main__":
    unittest.main(verbosity=2)
