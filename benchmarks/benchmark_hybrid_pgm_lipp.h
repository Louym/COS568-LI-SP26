#pragma once
#include "benchmark.h"

// ── Milestone 2: Naive (synchronous) hybrid ──────────────────────────────────
template <typename Searcher>
void benchmark_64_hybrid_pgm_lipp(tli::Benchmark<uint64_t>& benchmark,
                                   bool pareto, const std::vector<int>& params);

template <int record>
void benchmark_64_hybrid_pgm_lipp(tli::Benchmark<uint64_t>& benchmark,
                                   const std::string& filename);

// ── Milestone 3: Async double-buffered hybrid ─────────────────────────────────
template <typename Searcher>
void benchmark_64_async_hybrid_pgm_lipp(tli::Benchmark<uint64_t>& benchmark,
                                         bool pareto,
                                         const std::vector<int>& params);

template <int record>
void benchmark_64_async_hybrid_pgm_lipp(tli::Benchmark<uint64_t>& benchmark,
                                         const std::string& filename);
