# Protocol Documentation
<a name="top"></a>

## Table of Contents

- [proto/faiss.proto](#proto/faiss.proto)
    - [HeatbeatResponse](#faiss.HeatbeatResponse)
    - [Neighbor](#faiss.Neighbor)
    - [SearchByIdRequest](#faiss.SearchByIdRequest)
    - [SearchByIdResponse](#faiss.SearchByIdResponse)
    - [SearchRequest](#faiss.SearchRequest)
    - [SearchResponse](#faiss.SearchResponse)
    - [Vector](#faiss.Vector)
  
    - [FaissService](#faiss.FaissService)
  
- [Scalar Value Types](#scalar-value-types)



<a name="proto/faiss.proto"></a>
<p align="right"><a href="#top">Top</a></p>

## proto/faiss.proto
Messages for Faiss searching services.


<a name="faiss.HeatbeatResponse"></a>

### HeatbeatResponse
Response of heatbeat.


| Field | Type | Label | Description |
| ----- | ---- | ----- | ----------- |
| message | [string](#string) |  | Return OK if server is working. |






<a name="faiss.Neighbor"></a>

### Neighbor
Single instance of Faiss searching results.


| Field | Type | Label | Description |
| ----- | ---- | ----- | ----------- |
| id | [uint64](#uint64) |  | ID of neighbor&#39;s id. |
| score | [float](#float) |  | Score of metric. This value depends on which metrics (typically L2 distance, Inner Product and so on) you used to build index. |






<a name="faiss.SearchByIdRequest"></a>

### SearchByIdRequest
Request for searching by ID.


| Field | Type | Label | Description |
| ----- | ---- | ----- | ----------- |
| id | [uint64](#uint64) |  | The ID for searching. |
| k | [uint64](#uint64) |  | How many results (neighbors) you want to get. |






<a name="faiss.SearchByIdResponse"></a>

### SearchByIdResponse
Response of searching by ID.


| Field | Type | Label | Description |
| ----- | ---- | ----- | ----------- |
| request_id | [uint64](#uint64) |  | The requested ID. |
| neighbors | [Neighbor](#faiss.Neighbor) | repeated | Neighbors of given ID. Requested ID is excluded. |






<a name="faiss.SearchRequest"></a>

### SearchRequest
Request for searching by query vector.


| Field | Type | Label | Description |
| ----- | ---- | ----- | ----------- |
| query | [Vector](#faiss.Vector) |  | The query vector for searching. Dimension must be same as subscribed vectors in index. |
| k | [uint64](#uint64) |  | How many results (neighbors) you want to get. |






<a name="faiss.SearchResponse"></a>

### SearchResponse
Response of searching by query vector.


| Field | Type | Label | Description |
| ----- | ---- | ----- | ----------- |
| neighbors | [Neighbor](#faiss.Neighbor) | repeated | Neighbors of given query. |






<a name="faiss.Vector"></a>

### Vector
Wrapper message for list of float32. This keeps compatible for vectors used on Faiss.


| Field | Type | Label | Description |
| ----- | ---- | ----- | ----------- |
| val | [float](#float) | repeated | The query vector for searching. Dimension must be same as subscribed vectors in index. |





 

 

 


<a name="faiss.FaissService"></a>

### FaissService


| Method Name | Request Type | Response Type | Description |
| ----------- | ------------ | ------------- | ------------|
| Heatbeat | [.google.protobuf.Empty](#google.protobuf.Empty) | [HeatbeatResponse](#faiss.HeatbeatResponse) | Check server is working. |
| Search | [SearchRequest](#faiss.SearchRequest) | [SearchResponse](#faiss.SearchResponse) | Search neighbors from query vector. |
| SearchById | [SearchByIdRequest](#faiss.SearchByIdRequest) | [SearchByIdResponse](#faiss.SearchByIdResponse) | Search neighbors from ID. |

 



## Scalar Value Types

| .proto Type | Notes | C++ | Java | Python | Go | C# | PHP | Ruby |
| ----------- | ----- | --- | ---- | ------ | -- | -- | --- | ---- |
| <a name="double" /> double |  | double | double | float | float64 | double | float | Float |
| <a name="float" /> float |  | float | float | float | float32 | float | float | Float |
| <a name="int32" /> int32 | Uses variable-length encoding. Inefficient for encoding negative numbers – if your field is likely to have negative values, use sint32 instead. | int32 | int | int | int32 | int | integer | Bignum or Fixnum (as required) |
| <a name="int64" /> int64 | Uses variable-length encoding. Inefficient for encoding negative numbers – if your field is likely to have negative values, use sint64 instead. | int64 | long | int/long | int64 | long | integer/string | Bignum |
| <a name="uint32" /> uint32 | Uses variable-length encoding. | uint32 | int | int/long | uint32 | uint | integer | Bignum or Fixnum (as required) |
| <a name="uint64" /> uint64 | Uses variable-length encoding. | uint64 | long | int/long | uint64 | ulong | integer/string | Bignum or Fixnum (as required) |
| <a name="sint32" /> sint32 | Uses variable-length encoding. Signed int value. These more efficiently encode negative numbers than regular int32s. | int32 | int | int | int32 | int | integer | Bignum or Fixnum (as required) |
| <a name="sint64" /> sint64 | Uses variable-length encoding. Signed int value. These more efficiently encode negative numbers than regular int64s. | int64 | long | int/long | int64 | long | integer/string | Bignum |
| <a name="fixed32" /> fixed32 | Always four bytes. More efficient than uint32 if values are often greater than 2^28. | uint32 | int | int | uint32 | uint | integer | Bignum or Fixnum (as required) |
| <a name="fixed64" /> fixed64 | Always eight bytes. More efficient than uint64 if values are often greater than 2^56. | uint64 | long | int/long | uint64 | ulong | integer/string | Bignum |
| <a name="sfixed32" /> sfixed32 | Always four bytes. | int32 | int | int | int32 | int | integer | Bignum or Fixnum (as required) |
| <a name="sfixed64" /> sfixed64 | Always eight bytes. | int64 | long | int/long | int64 | long | integer/string | Bignum |
| <a name="bool" /> bool |  | bool | boolean | boolean | bool | bool | boolean | TrueClass/FalseClass |
| <a name="string" /> string | A string must always contain UTF-8 encoded or 7-bit ASCII text. | string | String | str/unicode | string | string | string | String (UTF-8) |
| <a name="bytes" /> bytes | May contain any arbitrary sequence of bytes. | string | ByteString | str | []byte | ByteString | string | String (ASCII-8BIT) |

