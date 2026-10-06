# System design basics interview questions

Q: How do you approach a system design question?
A: Clarify requirements and scale, define the API and data model, sketch a high-level design, then deep-dive on bottlenecks, trade-offs, failures and monitoring.

Q: Vertical versus horizontal scaling?
A: Vertical scaling adds power to one machine and is simple but limited. Horizontal scaling adds machines behind a load balancer; it scales further but requires stateless services and data partitioning.

Q: What does a load balancer do?
A: It distributes requests across servers using strategies like round robin or least connections, performs health checks, and removes failed nodes to improve availability.

Q: Explain caching and invalidation.
A: Caches such as Redis store hot data to cut latency and database load. Strategies include cache-aside, write-through and TTLs; invalidation is hard, so choose an acceptable staleness.

Q: SQL versus NoSQL: how do you choose?
A: SQL suits structured data, joins and strong transactions. NoSQL suits flexible schemas, huge scale or simple access patterns. Choose by access patterns and consistency needs.

Q: What is the CAP theorem?
A: During a network partition a distributed system must choose between consistency and availability. Many systems pick availability with eventual consistency; others prefer consistency.

Q: What is database sharding?
A: Splitting data across databases by a shard key such as user id to scale writes and storage. Challenges include hot shards, cross-shard queries and rebalancing.

Q: Why use a message queue?
A: Queues like Kafka or RabbitMQ decouple producers from consumers, absorb traffic spikes, allow retries and enable asynchronous processing.

Q: How would you design a URL shortener?
A: Generate unique short keys, for example base62 of an incrementing id, store key to URL in a key-value store, cache popular links, and use redirects with analytics handled asynchronously.

Q: What is rate limiting?
A: Restricting requests per client in a time window using algorithms like token bucket, protecting services from abuse and overload, typically enforced at the gateway with a shared counter store.

Q: How do you make a system highly available?
A: Remove single points of failure with redundancy across zones, use health checks and automatic failover, replicate data, deploy gradually and monitor with alerts.

Q: What is the difference between latency and throughput?
A: Latency is time for one request; throughput is requests handled per unit time. Optimizing one can affect the other, so measure both, including p95 and p99 latency.
