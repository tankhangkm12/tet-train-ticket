# Layer guide — what to dig out at each layer

Follow **one operation of the user's workload** (e.g. one GET, one produce, one HTTP request) down the stack. At
each layer answer the questions, name the mechanism, count its cost, and give a command that shows it.

## L1 Application / API
- What exactly does the client send? Wire format (text/binary), size per operation, batching/pipelining API.
- Serialization cost: schema-less vs schema (JSON, RESP, Protobuf, Avro), copies made by the client library.
- Observe: client debug logs, `tcpdump -A`, the library's metrics.

## L2 Runtime / engine
- Data structure that serves the operation (hash table, B+tree, LSM-tree, skip list, append-only log, ring
  buffer) and its complexity for this workload; memory layout (contiguous vs pointer-chasing).
- Concurrency model: single thread + event loop, thread per connection, thread pool, actor, shard-per-core;
  where locks are, and what is lock-free.
- Memory: allocator (jemalloc, arena), GC pauses (JVM/Go), eviction policy, copy-on-write.
- Durability: WAL, group commit, batching, compaction.
- Observe: `perf top -p <pid>`, flame graph, `INFO`/`EXPLAIN`/`jcmd`, GC logs.

## L3 OS / kernel
- Syscalls per operation (`read/write`, `sendfile`, `splice`, `mmap`, `io_uring_enter`, `epoll_wait`, `fsync`).
- I/O model: blocking, `epoll`/`kqueue` readiness, `io_uring` completion; how many fds one thread serves.
- Copies: user↔kernel copies; zero-copy (`sendfile`, `splice`, `MSG_ZEROCOPY`); page cache reliance vs
  `O_DIRECT`.
- Scheduling: context switches, thread count vs cores, CPU pinning.
- Observe: `strace -c -f -p <pid>`, `perf stat -e context-switches`, `vmstat 1`, `/proc/<pid>/status`,
  `bpftrace`/`bcc` (`biolatency`, `offcputime`).

## L4 Network
- Protocol and framing (TCP/UDP/QUIC, length-prefixed, HTTP/1.1 vs HTTP/2 multiplexing, gRPC).
- Round-trips per operation; pipelining; connection reuse/pooling; TLS handshakes.
- TCP behaviour: Nagle/`TCP_NODELAY`, delayed ACK, buffer sizes, backlog, keepalive.
- Replication/consensus traffic between nodes (Raft/Paxos, leader/follower, quorum acks).
- Observe: `ss -ti`, `tcpdump`/Wireshark, `nstat`, `ping`/`mtr` for the RTT baseline.

## L5 Hardware (only when it changes the answer)
- CPU cache: cache-line friendly layouts, false sharing; branch prediction.
- Storage: sequential vs random I/O (why LSM/append logs win on writes), SSD write amplification.
- NUMA, memory bandwidth, NIC offloads (RSS, TSO/GRO).
- Observe: `perf stat -e cache-misses`, `iostat -x 1`, `numastat`.

## Mechanisms that often explain "why it is fast"

| Mechanism | Wins because | Costs |
|---|---|---|
| single-threaded event loop | no locks, no context switches | one core per instance; a slow command blocks all |
| batching / group commit | one syscall / fsync for many ops | added latency per op |
| append-only log + sequential I/O | disk/SSD best case, page cache readahead | compaction, read amplification |
| zero-copy (`sendfile`/`splice`) | no user-space copy, fewer syscalls | data cannot be transformed on the way |
| LSM-tree | random writes become sequential | read/space amplification, compaction stalls |
| B+tree | few page reads per lookup, range scans | write amplification on random inserts |
| shard-per-core | no cross-core sharing | uneven keys → hot shard |
| pipelining / multiplexing | fewer round-trips | head-of-line blocking (HTTP/1.1, TCP) |
| copy-on-write snapshot (`fork`) | snapshot without stopping writes | memory doubling under heavy writes |
