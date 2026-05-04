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
    // Sweep over (pgm_error, flush_threshold) pairs
    benchmark.template Run<AsyncHybridPGMLipp<uint64_t, Searcher,  64,  10000>>();
    benchmark.template Run<AsyncHybridPGMLipp<uint64_t, Searcher,  64,  25000>>();
    benchmark.template Run<AsyncHybridPGMLipp<uint64_t, Searcher,  64,  50000>>();
    benchmark.template Run<AsyncHybridPGMLipp<uint64_t, Searcher,  64, 100000>>();
    benchmark.template Run<AsyncHybridPGMLipp<uint64_t, Searcher, 128,  25000>>();
    benchmark.template Run<AsyncHybridPGMLipp<uint64_t, Searcher, 128,  50000>>();
  }
}

template <int record>
void benchmark_64_async_hybrid_pgm_lipp(tli::Benchmark<uint64_t>& benchmark,
                                         const std::string& filename) {
  if (filename.find("0.900000i") != std::string::npos) {
    // Insert-heavy: larger threshold amortises flush overhead better.
    benchmark.template Run<AsyncHybridPGMLipp<uint64_t, BranchingBinarySearch<record>,  64,  50000>>();
    benchmark.template Run<AsyncHybridPGMLipp<uint64_t, BranchingBinarySearch<record>,  64, 100000>>();
    benchmark.template Run<AsyncHybridPGMLipp<uint64_t, BranchingBinarySearch<record>, 128,  50000>>();
  } else if (filename.find("0.100000i") != std::string::npos) {
    // Lookup-heavy: smaller threshold keeps DPGM tiny so lookups hit LIPP fast.
    benchmark.template Run<AsyncHybridPGMLipp<uint64_t, BranchingBinarySearch<record>,  64,  10000>>();
    benchmark.template Run<AsyncHybridPGMLipp<uint64_t, BranchingBinarySearch<record>,  64,  25000>>();
    benchmark.template Run<AsyncHybridPGMLipp<uint64_t, BranchingBinarySearch<record>, 128,  25000>>();
  } else {
    benchmark.template Run<AsyncHybridPGMLipp<uint64_t, BranchingBinarySearch<record>,  64,  50000>>();
    benchmark.template Run<AsyncHybridPGMLipp<uint64_t, BranchingBinarySearch<record>,  64, 100000>>();
    benchmark.template Run<AsyncHybridPGMLipp<uint64_t, BranchingBinarySearch<record>, 128,  50000>>();
  }
}

INSTANTIATE_TEMPLATES_MULTITHREAD(benchmark_64_async_hybrid_pgm_lipp, uint64_t);
