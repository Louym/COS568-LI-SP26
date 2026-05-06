#include "benchmarks/benchmark_hybrid_pgm_lipp.h"

#include "benchmark.h"
#include "benchmarks/common.h"
#include "competitors/hybrid_pgm_lipp.h"

// ════════════════════════════════════════════════════════════════════════════
// Milestone 2 – Naive (synchronous) HybridPGMLipp
// ════════════════════════════════════════════════════════════════════════════

template <typename Searcher>
void benchmark_64_hybrid_pgm_lipp(tli::Benchmark<uint64_t>& benchmark,
                                   bool pareto, const std::vector<int>& params) {
  if (!pareto) {
    util::fail("HybridPGMLipp's hyperparameter cannot be set directly");
  } else {
    benchmark.template Run<HybridPGMLipp<uint64_t, Searcher, 64,  5>>();
    benchmark.template Run<HybridPGMLipp<uint64_t, Searcher, 64, 10>>();
    benchmark.template Run<HybridPGMLipp<uint64_t, Searcher, 64, 20>>();
    benchmark.template Run<HybridPGMLipp<uint64_t, Searcher, 128,  5>>();
    benchmark.template Run<HybridPGMLipp<uint64_t, Searcher, 128, 10>>();
    benchmark.template Run<HybridPGMLipp<uint64_t, Searcher, 256,  5>>();
  }
}

template <int record>
void benchmark_64_hybrid_pgm_lipp(tli::Benchmark<uint64_t>& benchmark,
                                   const std::string& filename) {
  if (filename.find("0.900000i") != std::string::npos) {
    benchmark.template Run<HybridPGMLipp<uint64_t, BranchingBinarySearch<record>, 64,  5>>();
    benchmark.template Run<HybridPGMLipp<uint64_t, BranchingBinarySearch<record>, 64, 10>>();
    benchmark.template Run<HybridPGMLipp<uint64_t, BranchingBinarySearch<record>, 128,  5>>();
  } else if (filename.find("0.100000i") != std::string::npos) {
    benchmark.template Run<HybridPGMLipp<uint64_t, BranchingBinarySearch<record>, 64, 10>>();
    benchmark.template Run<HybridPGMLipp<uint64_t, BranchingBinarySearch<record>, 64, 20>>();
    benchmark.template Run<HybridPGMLipp<uint64_t, BranchingBinarySearch<record>, 128, 10>>();
  } else {
    benchmark.template Run<HybridPGMLipp<uint64_t, BranchingBinarySearch<record>, 64,  5>>();
    benchmark.template Run<HybridPGMLipp<uint64_t, BranchingBinarySearch<record>, 64, 10>>();
    benchmark.template Run<HybridPGMLipp<uint64_t, BranchingBinarySearch<record>, 128,  5>>();
  }
}

INSTANTIATE_TEMPLATES_MULTITHREAD(benchmark_64_hybrid_pgm_lipp, uint64_t);


// ════════════════════════════════════════════════════════════════════════════
// Milestone 3 – Async double-buffered AsyncHybridPGMLipp
//
// FlushThreshold is an absolute key count (not a percentage).  The active DPGM
// buffer is moved to a "flushing" slot and drained into LIPP by a background
// thread while new insertions continue into a fresh active buffer.
// ════════════════════════════════════════════════════════════════════════════

template <typename Searcher>
void benchmark_64_async_hybrid_pgm_lipp(tli::Benchmark<uint64_t>& benchmark,
                                         bool pareto,
                                         const std::vector<int>& params) {
  if (!pareto) {
    util::fail("AsyncHybridPGMLipp's hyperparameter cannot be set directly");
  } else {
    // Sweep all (pgm_error, flush_threshold) pairs + LIPP-direct baseline.
    benchmark.template Run<LippDirectHybrid<uint64_t, Searcher>>();
    benchmark.template Run<AsyncHybridPGMLipp<uint64_t, Searcher,  64,   10000>>();
    benchmark.template Run<AsyncHybridPGMLipp<uint64_t, Searcher,  64,   50000>>();
    benchmark.template Run<AsyncHybridPGMLipp<uint64_t, Searcher,  64,  100000>>();
    benchmark.template Run<AsyncHybridPGMLipp<uint64_t, Searcher,  64, 2000000>>();
    benchmark.template Run<AsyncHybridPGMLipp<uint64_t, Searcher, 128,  50000>>();
    benchmark.template Run<AsyncHybridPGMLipp<uint64_t, Searcher, 128, 2000000>>();
  }
}

template <int record>
void benchmark_64_async_hybrid_pgm_lipp(tli::Benchmark<uint64_t>& benchmark,
                                         const std::string& filename) {
  if (filename.find("0.900000i") != std::string::npos) {
    // Insert-heavy (90% insert): DPGM base + flat hash buffer.
    // New inserts go into a pre-allocated open-addressing hash table (O(1),
    // ~100 ns/op) instead of the DynamicPGM cascade (O(log^2 n), ~300 ns/op).
    // Lookups fall through to the static base DPGM which has only ONE large
    // sorted level after the range constructor — no 1.8M cascade overhead.
    benchmark.template Run<DpgmHashHybrid<uint64_t, BranchingBinarySearch<record>,  64>>();
    benchmark.template Run<DpgmHashHybrid<uint64_t, BranchingBinarySearch<record>, 128>>();
    // Keep the never-flush async variants as additional competitors.
    benchmark.template Run<AsyncHybridPGMLipp<uint64_t, BranchingBinarySearch<record>,  64, 2000000>>();
    benchmark.template Run<AsyncHybridPGMLipp<uint64_t, BranchingBinarySearch<record>, 128, 2000000>>();
  } else if (filename.find("0.100000i") != std::string::npos) {
    // Lookup-heavy (10% insert): direct LIPP strategy.
    // All operations go straight to LIPP — no DPGM overhead on the 90% of
    // ops that are lookups.  Achieves near-pure-LIPP throughput.
    benchmark.template Run<LippDirectHybrid<uint64_t, BranchingBinarySearch<record>>>();
    // Also include a fast-flush async variant as a fallback comparison.
    benchmark.template Run<AsyncHybridPGMLipp<uint64_t, BranchingBinarySearch<record>,  64,  10000>>();
    benchmark.template Run<AsyncHybridPGMLipp<uint64_t, BranchingBinarySearch<record>,  64,  25000>>();
  } else {
    benchmark.template Run<AsyncHybridPGMLipp<uint64_t, BranchingBinarySearch<record>,  64, 2000000>>();
    benchmark.template Run<AsyncHybridPGMLipp<uint64_t, BranchingBinarySearch<record>,  64,  100000>>();
    benchmark.template Run<LippDirectHybrid<uint64_t, BranchingBinarySearch<record>>>();
  }
}

INSTANTIATE_TEMPLATES_MULTITHREAD(benchmark_64_async_hybrid_pgm_lipp, uint64_t);
